from io import BytesIO

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (NameObject, DictionaryObject, DecodedStreamObject,
                           ArrayObject, FloatObject, TextStringObject)

from redact_studio.core import ImageError, Shape, render, write_unique
from redact_studio.pdf import load_pdf as _load_pdf, pdf_from_bytes as _pdf_from_bytes, encode_pdf, preview_pdf as _preview_pdf


# Keep established security fixtures at 200 DPI; resolution cases below test all new options.
def load_pdf(path, **kwargs):
    return _load_pdf(path, dpi=200, **kwargs)


def pdf_from_bytes(data, **kwargs):
    return _pdf_from_bytes(data, dpi=200, **kwargs)


def preview_pdf(data, index):
    return _preview_pdf(data, index, dpi=200)


def synthetic_pdf(pages=2, rotate=False, encrypted=False):
    writer = PdfWriter()
    for index in range(pages):
        page = writer.add_blank_page(width=144+index*36, height=144)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                                 NameObject('/Subtype'): NameObject('/Type1'),
                                 NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({
            NameObject('/F1'): writer._add_object(font)})})
        content = DecodedStreamObject()
        content.set_data(b'BT /F1 12 Tf 15 110 Td (Fictional private text) Tj ET\n1 0 0 rg 20 20 50 30 re f\n')
        page[NameObject('/Contents')] = writer._add_object(content)
        if rotate and index == 1:
            page.rotate(90)
        note = DictionaryObject({NameObject('/Type'): NameObject('/Annot'),
                                 NameObject('/Subtype'): NameObject('/Text'),
                                 NameObject('/Rect'): ArrayObject([FloatObject(v) for v in (5,5,15,15)]),
                                 NameObject('/Contents'): TextStringObject('Fictional annotation')})
        page[NameObject('/Annots')] = ArrayObject([writer._add_object(note)])
    writer.add_metadata({'/Author': 'Fictional Author', '/Title': 'Fictional secret title'})
    writer.add_attachment('fictional-secret.txt', b'Fictional secret attachment')
    writer.root_object[NameObject('/OpenAction')] = writer._add_object(DictionaryObject({
        NameObject('/S'): NameObject('/JavaScript'),
        NameObject('/JS'): TextStringObject("app.alert('Fictional JavaScript must never survive');")}))
    metadata = DecodedStreamObject()
    metadata.set_data(b'<x:xmpmeta>Fictional XMP author</x:xmpmeta>')
    metadata[NameObject('/Type')] = NameObject('/Metadata')
    metadata[NameObject('/Subtype')] = NameObject('/XML')
    writer.root_object[NameObject('/Metadata')] = writer._add_object(metadata)
    if encrypted:
        writer.encrypt('fictional-password')
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


@pytest.fixture
def pdf_file(tmp_path):
    source = tmp_path/'fictional.pdf'
    source.write_bytes(synthetic_pdf(rotate=True))
    return source


def test_pdf_roundtrip_pixels_objects_metadata_and_source(pdf_file):
    original = pdf_file.read_bytes()
    mtime = pdf_file.stat().st_mtime_ns
    book = load_pdf(pdf_file)
    assert len(book.pages) == 2
    assert book.sizes == [(144,144),(144,180)]
    assert book.pages[0].pixels.size == (400,400)
    book.pages[0].commit([Shape('rect',((0,0),(400,200)))])
    first = render(book.pages[0])
    data = encode_pdf(book)
    assert b'Fictional' not in data
    reader = PdfReader(BytesIO(data), strict=True)
    assert reader.metadata is None
    assert set(reader.trailer) == {'/Size','/Root'}
    assert set(reader.root_object) == {'/Type','/Pages'}
    assert len(reader.pages) == 2
    for index, page in enumerate(reader.pages):
        assert page.extract_text() == ''
        assert not any(key in page for key in ('/Annots','/Metadata','/Thumb','/Rotate','/AA'))
        assert '/Font' not in page['/Resources']
        images = list(page.images)
        assert len(images) == 1
        image = images[0].image.convert('RGB')
        expected = first if index == 0 else render(book.load_page(index))
        assert image.size == expected.size
        assert image.tobytes() == expected.tobytes()
        assert tuple(float(v) for v in page.mediabox)[2:] == book.sizes[index]
    assert preview_pdf(data, 0).getpixel((100,100)) == (0,0,0)
    assert pdf_file.read_bytes() == original
    assert pdf_file.stat().st_mtime_ns == mtime
    with pytest.raises(ImageError):
        write_unique(data, pdf_file, [pdf_file])


def test_lazy_page_cache_and_independent_history(pdf_file):
    book = load_pdf(pdf_file)
    page0 = book.pages[0]
    page0.commit([Shape('brush',((20,20),(200,200)),width=12)])
    page1 = book.load_page(1)
    assert page0.pixels is None and page1.pixels is not None
    assert not page1.shapes
    book.load_page(0)
    page0.undo(); assert not page0.shapes
    page0.redo(); assert len(page0.shapes) == 1
    assert page1.pixels is None


@pytest.mark.parametrize('limit,value', [('MAX_PDF_PAGES',1),('MAX_PDF_PAGE_PIXELS',100),
                                        ('MAX_PDF_TOTAL_PIXELS',100),('MAX_PDF_BYTES',100)])
def test_preflight_limits(pdf_file, monkeypatch, limit, value):
    import redact_studio.pdf as module
    monkeypatch.setattr(module, limit, value)
    with pytest.raises(ImageError):
        load_pdf(pdf_file)


def test_bad_and_encrypted_pdf(tmp_path):
    path = tmp_path/'bad.pdf'; path.write_bytes(b'not a PDF')
    with pytest.raises(ImageError): load_pdf(path)
    path.write_bytes(synthetic_pdf(encrypted=True))
    with pytest.raises(ImageError): load_pdf(path)


def test_export_failure_is_closed_and_does_not_mutate_editor(pdf_file, monkeypatch):
    import redact_studio.pdf as module
    book = load_pdf(pdf_file)
    cached = book.pages[0].pixels
    original_raster = book.raster
    def fail_second(index):
        if index == 1: raise ImageError('Synthetic render failure')
        return original_raster(index)
    monkeypatch.setattr(book, 'raster', fail_second)
    with pytest.raises(ImageError): encode_pdf(book)
    assert book.pages[0].pixels is cached
    monkeypatch.setattr(book, 'raster', original_raster)
    monkeypatch.setattr(module, 'MAX_OUTPUT_BYTES', 100)
    with pytest.raises(ImageError): encode_pdf(book)


def test_pdf_preview_orientation_matches_output_image(pdf_file):
    book = load_pdf(pdf_file)
    data = encode_pdf(book)
    for index in range(2):
        image = preview_pdf(data,index)
        expected = render(book.load_page(index))
        assert image.size == expected.size
        # Exact sampling at integer render dimensions with PDF image interpolation disabled.
        assert image.tobytes() == expected.tobytes()


def test_pdf_editor_switch_and_whole_document_review(app, pdf_file):
    from redact_studio.window import Window
    from redact_studio.pdf_ui import PdfEditor, PdfReview
    from PySide6.QtWidgets import QDialog
    window = Window()
    book = load_pdf(pdf_file)
    window.add_document(book)
    editor = window.tabs.currentWidget()
    assert isinstance(editor, PdfEditor)
    book.pages[0].commit([Shape('rect',((0,0),(200,200)))])
    editor.number.setValue(2)
    assert window.canvas().document is book.pages[1]
    assert window.subject() is book
    window.canvas().document.commit([Shape('brush',((10,10),(40,40)))])
    editor.number.setValue(1)
    assert len(window.canvas().document.shapes) == 1
    window.history(False); assert not book.pages[0].shapes
    assert book.pages[1].shapes
    review = PdfReview(book, window.defaults, window)
    assert 'NO redactions' in review.confirm.text()
    assert review.overview.count() == 2
    assert 'NO redactions' in review.overview.item(0).text()
    review.accept(); assert review.result() != QDialog.Accepted
    review.confirm.setChecked(True)
    assert review.save_button.isEnabled()
    review.open_detail(review.overview.item(1))
    assert review.number.value() == 2
    assert review.views.currentIndex() == 1
    assert review.confirm.isChecked()
    review.views.setCurrentIndex(0)
    review.confirm.setChecked(False)
    assert not review.save_button.isEnabled()
    review.confirm.setChecked(True)
    review.accept(); assert review.result() == QDialog.Accepted
    window.tabs.clear(); window.close()


def test_pdf_export_route_and_mixed_batch_subjects(app, pdf_file, tmp_path, monkeypatch):
    from redact_studio.window import Window
    from redact_studio.pdf_ui import PdfReview
    from redact_studio.core import Document
    from PySide6.QtWidgets import QDialog
    window = Window()
    window.import_paths([str(pdf_file)])
    book = window.subject()
    assert len(book.pages) == 2
    window.add_document(Document(Image.new('RGBA',(10,10),'white')))
    assert window.subject(0) is book
    assert window.subject(1).pdf_book is None
    target = tmp_path/'output.png'
    def approve(dialog):
        dialog.destination.setText(str(target))
        dialog.confirm.setChecked(True)
        dialog.accept()
        return dialog.result()
    monkeypatch.setattr(PdfReview, 'exec', approve)
    output = window.export_document(book)
    assert output == tmp_path/'output.pdf'
    assert len(PdfReader(output).pages) == 2
    assert not target.exists()
    window.tabs.clear(); window.close()


def test_review_preview_failure_disables_pdf_export(app, pdf_file, monkeypatch):
    import redact_studio.pdf_ui as module
    from PySide6.QtWidgets import QMessageBox, QDialog
    review = module.PdfReview(load_pdf(pdf_file), {'directory':'','suffix':'_REDACTED'})
    review.confirm.setChecked(True)
    def fail(*args): raise MemoryError('Synthetic preview failure')
    monkeypatch.setattr(module, 'preview_pdf', fail)
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: QMessageBox.Ok)
    review.number.setValue(2)
    assert review.data is None and not review.save_button.isEnabled()
    assert not review.confirm.isChecked()
    assert review.overview.count() == 0
    review.accept(); assert review.result() != QDialog.Accepted
    review.close()


def test_pdf_render_snapshot_and_counterfactual_mask(tmp_path, monkeypatch):
    import socket
    def blocked(*args, **kwargs): raise AssertionError('Network use is forbidden')
    monkeypatch.setattr(socket, 'socket', blocked)
    source = tmp_path/'source.pdf'
    raw = synthetic_pdf(pages=1)
    source.write_bytes(raw)
    book = load_pdf(source)
    source.write_bytes(b'File changed after import')
    assert book.raster(0).size == (400,400)
    a = pdf_from_bytes(raw)
    b = pdf_from_bytes(raw.replace(b'Fictional private text',b'Different private text'))
    for item in (a,b):
        item.pages[0].commit([Shape('rect',((0,0),(400,200)))])
    assert encode_pdf(a) == encode_pdf(b)


def test_standard_form_appearance_is_flattened_but_fields_removed():
    from pypdf.generic import BooleanObject
    writer = PdfWriter(BytesIO(synthetic_pdf(pages=1)))
    appearance = DecodedStreamObject()
    appearance.set_data(b'0 0 1 rg 0 0 60 25 re f')
    appearance.update({NameObject('/Type'): NameObject('/XObject'),
                       NameObject('/Subtype'): NameObject('/Form'),
                       NameObject('/BBox'): ArrayObject([FloatObject(v) for v in (0,0,60,25)]),
                       NameObject('/Resources'): DictionaryObject()})
    widget = DictionaryObject({
        NameObject('/Type'): NameObject('/Annot'), NameObject('/Subtype'): NameObject('/Widget'),
        NameObject('/FT'): NameObject('/Tx'), NameObject('/T'): TextStringObject('FictionalField'),
        NameObject('/V'): TextStringObject('Fictional secret value'),
        NameObject('/Rect'): ArrayObject([FloatObject(v) for v in (70,60,130,85)]),
        NameObject('/AP'): DictionaryObject({NameObject('/N'): writer._add_object(appearance)})})
    field = writer._add_object(widget)
    writer.pages[0]['/Annots'].append(field)
    writer.root_object[NameObject('/AcroForm')] = writer._add_object(DictionaryObject({
        NameObject('/Fields'): ArrayObject([field]), NameObject('/NeedAppearances'): BooleanObject(False)}))
    buffer = BytesIO(); writer.write(buffer)
    book = pdf_from_bytes(buffer.getvalue())
    assert book.pages[0].pixels.getpixel((278,200))[:3] == (0,0,255)
    book.pages[0].commit([Shape('rect',((270,190),(290,210)))])
    data = encode_pdf(book)
    assert '/AcroForm' not in PdfReader(BytesIO(data)).root_object
    assert b'FictionalField' not in data
    assert preview_pdf(data,0).getpixel((278,200)) == (0,0,0)


def test_cropbox_and_empty_password_encryption():
    writer = PdfWriter(BytesIO(synthetic_pdf(pages=1)))
    writer.pages[0].cropbox.lower_left = (10,10)
    writer.pages[0].cropbox.upper_right = (130,130)
    buffer = BytesIO(); writer.write(buffer)
    book = pdf_from_bytes(buffer.getvalue())
    assert book.sizes == [(120,120)]
    assert tuple(PdfReader(BytesIO(encode_pdf(book))).pages[0].mediabox)[2:] == (120,120)
    writer.encrypt('')
    buffer = BytesIO(); writer.write(buffer)
    with pytest.raises(ImageError): pdf_from_bytes(buffer.getvalue())


def test_aggregate_pdf_source_budget(app, pdf_file, monkeypatch):
    import redact_studio.window as module
    window = module.Window()
    book = load_pdf(pdf_file)
    monkeypatch.setattr(module, 'MAX_OPEN_PDF_BYTES', len(book.source_bytes))
    window.add_document(book)
    with pytest.raises(ImageError): window.add_document(load_pdf(pdf_file))
    assert window.tabs.count() == 1
    window.tabs.clear(); window.close()


def test_all_page_thumbnails_use_actual_sanitised_output(pdf_file):
    from redact_studio.pdf import preview_pdf_pages
    book = load_pdf(pdf_file)
    book.pages[0].commit([Shape('rect', ((0,0),(400,200)))])
    pages = preview_pdf_pages(encode_pdf(book), max_size=240)
    assert len(pages) == 2
    assert all(max(page.size) <= 240 for page in pages)
    assert pages[0].getpixel((30,30)) == (0,0,0)
    assert pages[1].height > pages[1].width


def test_incomplete_overview_cannot_be_exported(app, pdf_file, monkeypatch):
    import redact_studio.pdf_ui as module
    from PySide6.QtWidgets import QMessageBox, QDialog
    monkeypatch.setattr(module, 'preview_pdf_pages', lambda *args: [Image.new('RGB',(10,10))])
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: QMessageBox.Ok)
    review = module.PdfReview(load_pdf(pdf_file), {'directory':'','suffix':'_REDACTED'})
    assert review.data is None
    assert not review.confirm.isEnabled()
    assert not review.save_button.isEnabled()
    review.accept(); assert review.result() != QDialog.Accepted
    review.close()


@pytest.mark.parametrize('dpi', [200, 300, 400, 600])
def test_pdf_resolution_and_redaction_alignment(dpi):
    from redact_studio.pdf import pdf_from_bytes, preview_pdf
    book = pdf_from_bytes(synthetic_pdf(pages=1), dpi=dpi)
    assert book.dpi == dpi
    assert book.pages[0].pixels.size == (dpi*2, dpi*2)
    # Redact the same physical top half at every resolution.
    book.pages[0].commit([Shape('rect', ((0,0),(dpi*2,dpi)))])
    data = encode_pdf(book)
    reader = PdfReader(BytesIO(data), strict=True)
    image = list(reader.pages[0].images)[0].image.convert('RGB')
    assert image.size == (dpi*2, dpi*2)
    assert image.getpixel((dpi,dpi//2)) == (0,0,0)
    assert tuple(reader.pages[0].mediabox)[2:] == (144,144)
    assert preview_pdf(data,0,dpi=dpi).tobytes() == image.tobytes()


def test_default_pdf_resolution_and_invalid_choice():
    from redact_studio.pdf import pdf_from_bytes
    book = pdf_from_bytes(synthetic_pdf(pages=1))
    assert book.dpi == 300
    assert book.pages[0].pixels.size == (600,600)
    with pytest.raises(ImageError): pdf_from_bytes(synthetic_pdf(pages=1), dpi=1200)


def test_pdf_resolution_choice_applies_only_to_new_documents(app, pdf_file):
    from redact_studio.window import Window
    window = Window()
    window.pdf_dpi = 300
    window.import_paths([str(pdf_file)])
    original = window.subject()
    original.pages[0].commit([Shape('rect', ((15,15),(100,100)))])
    window.pdf_dpi = 400
    window.import_paths([str(pdf_file)])
    assert window.subject().dpi == 400
    assert original.dpi == 300
    assert original.pages[0].shapes[0].points == ((15,15),(100,100))
    window.tabs.clear(); window.close()


def test_a4_at_600_dpi_and_oversized_page_rejection():
    from redact_studio.pdf import pdf_from_bytes
    writer = PdfWriter()
    writer.add_blank_page(width=595,height=842)
    buffer = BytesIO(); writer.write(buffer)
    book = pdf_from_bytes(buffer.getvalue(), dpi=600)
    assert book.pages[0].pixels.size == (4959,7017)
    book.pages[0].pixels = None
    writer = PdfWriter()
    writer.add_blank_page(width=842,height=1191)
    buffer = BytesIO(); writer.write(buffer)
    with pytest.raises(ImageError, match='lower PDF resolution'):
        pdf_from_bytes(buffer.getvalue(), dpi=600)
