"""Pixel-only pipeline. No source bytes or metadata enter an output encoder."""
from dataclasses import dataclass, field, replace
from io import BytesIO
from pathlib import Path
import math
import os
import warnings
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

MAX_PIXELS = 24_000_000
MAX_DOCUMENT_PIXELS = 48_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS
SUPPORTED = {'PNG', 'JPEG', 'BMP', 'TIFF', 'WEBP'}

class ImageError(ValueError):
    pass

@dataclass(frozen=True)
class Shape:
    kind: str
    points: tuple
    color: str = '#000000'
    width: int = 24

    @property
    def bounds(self):
        xs, ys = zip(*self.points)
        pad = self.width / 2 if self.kind == 'brush' else 0
        return min(xs)-pad, min(ys)-pad, max(xs)+pad, max(ys)+pad

    def moved(self, dx, dy):
        return replace(self, points=tuple((x+dx, y+dy) for x, y in self.points))

@dataclass
class Document:
    pixels: Image.Image | None
    source: Path | None = None
    name: str = 'Clipboard'
    shapes: list = field(default_factory=list)
    undo_stack: list = field(default_factory=list)
    redo_stack: list = field(default_factory=list)
    pdf_book: object | None = field(default=None, repr=False)
    page_index: int = 0

    def commit(self, shapes):
        if list(shapes) == self.shapes:
            return
        self.undo_stack.append(tuple(self.shapes))
        self.undo_stack = self.undo_stack[-100:]
        self.redo_stack.clear()
        self.shapes = list(shapes)

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(tuple(self.shapes))
            self.shapes = list(self.undo_stack.pop())

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(tuple(self.shapes))
            self.shapes = list(self.redo_stack.pop())


def load_image(path):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(path, formats=sorted(SUPPORTED)) as source:
                if source.format not in SUPPORTED:
                    raise ImageError('Unsupported image format.')
                if getattr(source, 'n_frames', 1) != 1:
                    raise ImageError('Multi-frame images are not supported. Import a single frame explicitly.')
                if source.width * source.height > MAX_PIXELS:
                    raise ImageError('Image exceeds the 24 megapixel limit.')
                source.load()
                oriented = ImageOps.exif_transpose(source)
                rgba = oriented.convert('RGBA')
                # Reconstruct from pixels to discard every inherited metadata dictionary.
                pixels = Image.frombytes('RGBA', rgba.size, rgba.tobytes())
        return Document(pixels, Path(path).resolve(), Path(path).stem)
    except ImageError:
        raise
    except Exception:
        raise ImageError('Image could not be loaded safely. It may be damaged or too large.') from None


def shape_mask(shape, size):
    mask = Image.new('1', size)
    draw = ImageDraw.Draw(mask)
    if shape.kind == 'rect':
        x0, y0, x1, y1 = shape.bounds
        box = (math.floor(x0), math.floor(y0), math.ceil(x1)-1, math.ceil(y1)-1)
        if box[2] >= box[0] and box[3] >= box[1]:
            draw.rectangle(box, fill=1)
    elif shape.kind == 'brush':
        radius = max(1, shape.width) / 2
        if len(shape.points) > 1:
            draw.line(shape.points, fill=1, width=max(1, math.ceil(shape.width)), joint='curve')
        for x, y in shape.points:
            draw.ellipse((math.floor(x-radius), math.floor(y-radius),
                          math.ceil(x+radius), math.ceil(y+radius)), fill=1)
    else:
        raise ImageError('Unknown redaction type; export stopped.')
    return mask


def render(document, jpeg=False):
    # Flatten transparent input against white; exports always contain opaque pixels.
    out = Image.new('RGB', document.pixels.size, 'white')
    out.paste(document.pixels, mask=document.pixels.getchannel('A'))
    for shape in document.shapes:
        mask = shape_mask(shape, out.size)
        if jpeg:
            # JPEG operates on 8x8 DCT blocks. Cover whole blocks, with no chroma
            # subsampling, so no unredacted pixels share a redacted block.
            box = mask.getbbox()
            if box:
                expanded = Image.new('1', out.size)
                d = ImageDraw.Draw(expanded)
                for y in range(box[1]//8*8, box[3], 8):
                    for x in range(box[0]//8*8, box[2], 8):
                        if mask.crop((x,y,x+8,y+8)).getbbox():
                            d.rectangle((x,y,x+7,y+7), fill=1)
                mask = expanded
        out.paste(shape.color, mask=mask)
    return Image.frombytes('RGB', out.size, out.tobytes())


def encode(document, fmt='PNG', quality=95, compression=6):
    if fmt not in {'PNG','JPEG','WEBP'}:
        raise ImageError('Unsupported export format.')
    image = render(document, jpeg=fmt == 'JPEG')
    buffer = BytesIO()
    options = {'compress_level': compression} if fmt == 'PNG' else (
        {'quality': quality, 'subsampling': 0} if fmt == 'JPEG' else {'lossless': True, 'exact': True})
    image.save(buffer, format=fmt, **options)
    return buffer.getvalue()


def decoded_preview(data):
    with Image.open(BytesIO(data)) as image:
        return image.convert('RGB').copy()


def write_unique(data, destination, sources=()):
    """Exclusive creation prevents overwrites, including symlinks and collisions."""
    destination = Path(destination)
    protected = {Path(p).resolve() for p in sources if p is not None}
    if destination.resolve() in protected:
        raise ImageError('Choose a different destination from every original source image.')
    for counter in range(10000):
        target = destination if counter == 0 else destination.with_stem(f'{destination.stem}_{counter}')
        if target.resolve() in protected:
            continue
        try:
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        try:
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return target
    raise ImageError('Too many filename collisions; choose another filename.')


def export_directory(source=None, configured=''):
    """An explicit preference overrides the source folder; clipboard uses home."""
    if configured:
        return Path(configured)
    return Path(source).parent if source is not None else Path.home()
