from io import BytesIO
from pathlib import Path
import hashlib
import struct
import pytest
from PIL import Image, PngImagePlugin
from redact_studio.core import (Document,Shape,ImageError,load_image,render,encode,
                               decoded_preview,write_unique,shape_mask)

@pytest.fixture
def document():
    image=Image.new('RGBA',(64,48))
    image.putdata([(x*3,y*5,(x+y)*2,255) for y in range(48) for x in range(64)])
    return Document(image)

@pytest.mark.parametrize('fmt',['PNG','JPEG','WEBP'])
def test_permanent_export(document,fmt):
    document.shapes=[Shape('rect',((11.2,9.1),(39.1,31.1)))]
    output=decoded_preview(encode(document,fmt))
    assert output.size==(64,48)
    # JPEG intentionally expands to full blocks; interior is exactly black.
    for y in range(9,32):
        for x in range(11,40): assert output.getpixel((x,y))==(0,0,0)


def test_brush_continuous_and_overlapping(document):
    document.shapes=[Shape('brush',((0,0),(63,47)),width=8),
                     Shape('rect',((20,20),(30,30)),color='#ffffff')]
    result=render(document)
    for t in range(64):
        x,y=t,round(t*47/63)
        assert result.getpixel((x,y)) == ((255,255,255) if 20<=x<30 and 20<=y<30 else (0,0,0))


def test_transparency_and_edge_clipping(document):
    document.pixels=Image.new('RGBA',(64,48),(255,0,0,0))
    document.shapes=[Shape('rect',((-5,-3),(3.2,4.1)))]
    result=render(document)
    assert result.getpixel((3,4))==(0,0,0)
    assert result.getpixel((4,4))==(255,255,255)
    assert result.mode=='RGB'


def test_history_geometry_only(document):
    original=document.pixels
    document.commit([Shape('rect',((1,2),(4,5)))])
    document.commit([document.shapes[0].moved(2,3)])
    document.undo(); assert document.shapes[0].points[0]==(1,2)
    document.redo(); assert document.shapes[0].points[0]==(3,5)
    assert document.pixels is original
    document.undo(); document.commit([]); assert not document.redo_stack


def png_chunks(data):
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    offset=8; chunks=[]
    while offset<len(data):
        n=struct.unpack('>I',data[offset:offset+4])[0]
        chunks.append(data[offset+4:offset+8]); offset+=n+12
    return chunks


def jpeg_segments(data):
    # Independent container parser stops at entropy-coded scan.
    assert data[:2]==b'\xff\xd8'
    pos=2; markers=[]
    while pos<len(data):
        assert data[pos]==255
        marker=data[pos+1]; pos+=2
        markers.append(marker)
        if marker in (0xda,0xd9): break
        size=int.from_bytes(data[pos:pos+2],'big'); pos+=size
    return markers


def webp_chunks(data):
    assert data[:4]==b'RIFF' and data[8:12]==b'WEBP'
    pos=12; chunks=[]
    while pos<len(data):
        chunks.append(data[pos:pos+4]); size=int.from_bytes(data[pos+4:pos+8],'little')
        pos+=8+size+(size%2)
    return chunks

@pytest.mark.parametrize('source_format',['PNG','JPEG','WEBP','TIFF'])
@pytest.mark.parametrize('output_format',['PNG','JPEG','WEBP'])
def test_metadata_and_source_integrity(tmp_path,source_format,output_format):
    image=Image.new('RGB',(40,24),'red')
    exif=Image.Exif()
    exif[270]='Fictional confidential description'
    exif[271]='Fictional Camera'
    exif[315]='Fictional Author'
    exif[306]='2001:02:03 04:05:06'
    exif[37510]=b'Fictional private comment'
    exif[34853]={1:'N',2:(51.,0.,0.),3:'W',4:(1.,0.,0.)}
    exif[274]=6
    kwargs={'exif':exif.tobytes()}
    if source_format=='PNG':
        text=PngImagePlugin.PngInfo(); text.add_text('Author','Fictional Author')
        text.add_itxt('XML:com.adobe.xmp','Fictional XMP')
        kwargs['pnginfo']=text
    if source_format=='WEBP': kwargs['xmp']=b'Fictional XMP'
    source=tmp_path/('source.'+source_format.lower())
    image.save(source,source_format,**kwargs)
    source_bytes=source.read_bytes(); source_stat=source.stat()
    d=load_image(source)
    assert d.pixels.size==(24,40)
    d.shapes=[Shape('rect',((0,0),(16,16)))]
    data=encode(d,output_format)
    assert b'Fictional' not in data and b'2001:02' not in data
    with Image.open(BytesIO(data)) as out:
        assert not out.getexif()
        assert not any(k in out.info for k in ('xmp','icc_profile','exif','Author','XML:com.adobe.xmp'))
        assert out.size==(24,40)
        assert out.convert('RGB').getpixel((4,4))==(0,0,0)
    if output_format=='PNG': assert set(png_chunks(data))<={b'IHDR',b'IDAT',b'IEND'}
    elif output_format=='JPEG':
        # Encoder-generated JFIF APP0 is structural; no EXIF/XMP/IPTC APP1/APP13.
        assert not set(jpeg_segments(data)) & {0xe1,0xed,0xfe}
    else: assert set(webp_chunks(data))<={b'VP8L',b'VP8X',b'ALPH',b'VP8 '}
    assert source.read_bytes()==source_bytes
    assert source.stat().st_mtime_ns==source_stat.st_mtime_ns


def test_collision_and_source_protection(tmp_path):
    source=tmp_path/'source.png'; source.write_bytes(b'original')
    with pytest.raises(ImageError): write_unique(b'output',source,[source])
    destination=tmp_path/'copy.png'
    assert write_unique(b'one',destination)==destination
    assert write_unique(b'two',destination)==tmp_path/'copy_1.png'
    assert destination.read_bytes()==b'one'
    with pytest.raises(OSError): write_unique(b'bad',tmp_path/'missing'/'image.png')


def test_interrupted_write_removes_partial(tmp_path,monkeypatch):
    import redact_studio.core as core
    def fail(fd): raise OSError('Synthetic disk failure')
    monkeypatch.setattr(core.os,'fsync',fail)
    target=tmp_path/'output.png'
    with pytest.raises(OSError): write_unique(b'data',target)
    assert not target.exists()


def test_fail_closed_invalid_shape(document):
    document.shapes=[Shape('unsupported',((1,1),(2,2)))]
    with pytest.raises(ImageError): encode(document)


def test_bad_input_and_multiframe(tmp_path):
    path=tmp_path/'bad.png'; path.write_bytes(b'not an image')
    with pytest.raises(ImageError): load_image(path)
    Image.new('RGB',(2,2)).save(path,'TIFF',save_all=True,append_images=[Image.new('RGB',(2,2))])
    with pytest.raises(ImageError): load_image(path)


def test_size_limit_before_decode(tmp_path,monkeypatch):
    import redact_studio.core as core
    path=tmp_path/'image.png'; Image.new('RGB',(11,11)).save(path)
    monkeypatch.setattr(core,'MAX_PIXELS',100)
    with pytest.raises(ImageError): load_image(path)


def test_symlink_destination_is_never_overwritten(tmp_path):
    source=tmp_path/'source.png'; source.write_bytes(b'original')
    link=tmp_path/'link.png'
    try:
        link.symlink_to(source)
    except OSError:
        pytest.skip('OS account does not permit creating symlinks')
    with pytest.raises(ImageError): write_unique(b'new',link,[source])
    assert source.read_bytes()==b'original'

@pytest.mark.parametrize('fmt',['PNG','JPEG','WEBP'])
def test_source_binary_app_segments_and_thumbnail_discarded(tmp_path,fmt):
    image=Image.new('RGB',(64,48),'red')
    buffer=BytesIO(); image.save(buffer,'JPEG')
    # Source-only APP1 thumbnail-like payload, APP13 IPTC and JPEG COM.
    payloads=[(b'\xff\xe1',b'http://ns.adobe.com/xap/1.0/\x00FICTIONAL_XMP'),
              (b'\xff\xed',b'Photoshop 3.0\x008BIM\x04\x04FICTIONAL_IPTC'),
              (b'\xff\xfe',b'FICTIONAL_COMMENT'),
              (b'\xff\xe2',b'FICTIONAL_EMBEDDED_THUMBNAIL')]
    segments=b''.join(marker+struct.pack('>H',len(data)+2)+data for marker,data in payloads)
    source=tmp_path/'source.jpg'
    source.write_bytes(buffer.getvalue()[:2]+segments+buffer.getvalue()[2:])
    d=load_image(source)
    result=encode(d,fmt)
    for marker,data in payloads: assert data not in result


def test_all_supported_input_modes(tmp_path):
    for mode,color in [('1',1),('L',90),('P',1),('RGB',(12,34,56)),('RGBA',(12,34,56,70)),('CMYK',(10,20,30,40))]:
        source=tmp_path/(mode+'.tiff')
        Image.new(mode,(8,6),color).save(source)
        d=load_image(source)
        assert d.pixels.mode=='RGBA'
        assert decoded_preview(encode(d)).size==(8,6)

@pytest.mark.parametrize('fmt',['PNG','JPEG','WEBP'])
def test_covered_source_changes_cannot_influence_export(fmt):
    # Counterfactual confidentiality check: source differences confined beneath
    # the mask must produce identical complete export bytes.
    a=Document(Image.new('RGBA',(32,32),'white'))
    b=Document(a.pixels.copy())
    for y in range(9,20):
        for x in range(9,20): b.pixels.putpixel((x,y),(x*10,y*10,33,255))
    a.shapes=b.shapes=[Shape('rect',((9,9),(20,20)))]
    assert encode(a,fmt)==encode(b,fmt)

@pytest.mark.parametrize('fmt',['PNG','JPEG','WEBP'])
def test_real_exif_ifd1_thumbnail_removed(tmp_path,fmt):
    thumbnail=BytesIO(); Image.new('RGB',(8,8),'blue').save(thumbnail,'JPEG')
    thumb=thumbnail.getvalue()
    # Little-endian TIFF: IFD0 (orientation), then IFD1 containing a JPEG thumbnail.
    tiff=b'II'+struct.pack('<HI',42,8)
    tiff+=struct.pack('<H',1)+struct.pack('<HHI',274,3,1)+struct.pack('<H',1)+b'\x00\x00'+struct.pack('<I',26)
    tiff+=struct.pack('<H',2)
    tiff+=struct.pack('<HHII',513,4,1,56)
    tiff+=struct.pack('<HHII',514,4,1,len(thumb))+struct.pack('<I',0)+thumb
    payload=b'Exif\x00\x00'+tiff
    source_data=BytesIO(); Image.new('RGB',(64,48),'red').save(source_data,'JPEG')
    raw=source_data.getvalue()
    source=tmp_path/'thumbnail-source.jpg'
    source.write_bytes(raw[:2]+b'\xff\xe1'+struct.pack('>H',len(payload)+2)+payload+raw[2:])
    assert thumb in source.read_bytes()
    output=encode(load_image(source),fmt)
    assert payload not in output and thumb not in output
    if fmt=='JPEG': assert 0xe1 not in jpeg_segments(output)


def test_unsupported_decoder_is_not_invoked(tmp_path, monkeypatch):
    """A misleading extension must not reach an unapproved Pillow opener."""
    source = tmp_path / 'disguised.png'
    source.write_bytes(b'%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 10 10\nshowpage\n')
    Image.init()
    calls = []

    def forbidden_decoder(*args, **kwargs):
        calls.append(True)
        raise AssertionError('Unsupported decoder must not be invoked')

    monkeypatch.setitem(Image.OPEN, 'EPS', (forbidden_decoder, lambda prefix: True))
    with pytest.raises(ImageError):
        load_image(source)
    assert not calls
