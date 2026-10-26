import pytest
from PIL import Image
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog
from redact_studio.core import Document, Shape, decoded_preview
from redact_studio.canvas import Canvas
from redact_studio.window import Window, Review

@pytest.mark.parametrize('zoom',[.1,.5,1,2,8])
def test_canvas_rectangle_coordinates(app,zoom):
    d=Document(Image.new('RGBA',(600,400),'red'))
    c=Canvas(d); c.resize(900,650); c.show(); app.processEvents()
    c.resetTransform(); c.scale(zoom,zoom)
    # Use visible centre to exercise scroll and transform mapping.
    center=c.mapToScene(c.viewport().rect().center())
    a=c.mapFromScene(center.x()-10,center.y()-10)
    b=c.mapFromScene(center.x()+10,center.y()+10)
    expected_a=c.point(a); expected_b=c.point(b)
    QTest.mousePress(c.viewport(),Qt.LeftButton,Qt.NoModifier,a)
    QTest.mouseMove(c.viewport(),b)
    QTest.mouseRelease(c.viewport(),Qt.LeftButton,Qt.NoModifier,b)
    assert len(d.shapes)==1
    assert d.shapes[0].points==(expected_a,expected_b)
    c.close()


def test_preview_bytes_and_confirmation(app):
    d=Document(Image.new('RGBA',(32,32),'red'))
    d.shapes=[Shape('rect',((4,4),(20,20)))]
    defaults={'format':'PNG','suffix':'_REDACTED','directory':'','quality':95,'compression':6}
    review=Review(d,defaults)
    assert not review.confirm.isChecked()
    assert review.preview_image.tobytes()==decoded_preview(review.data).tobytes()
    review.confirm.setChecked(True)
    review.format.setCurrentText('JPEG')
    assert not review.confirm.isChecked()
    assert review.preview_image.getpixel((8,8))==(0,0,0)
    review.close()


def test_multiple_documents_history_and_sanitised_clipboard(app):
    window=Window()
    a=Document(Image.new('RGBA',(32,32),'red'),name='One')
    b=Document(Image.new('RGBA',(20,20),'blue'),name='Two')
    window.add_document(a); window.add_document(b)
    a.commit([Shape('rect',((0,0),(16,16)))])
    assert not b.shapes
    window.tabs.setCurrentIndex(0)
    window.history(False); assert not a.shapes
    window.history(True); assert len(a.shapes)==1
    # Same QImage conversion used by clipboard export contains only output pixels.
    from redact_studio.canvas import pixmap
    image=decoded_preview(__import__('redact_studio.core',fromlist=['encode']).encode(a))
    app.clipboard().setImage(pixmap(image).toImage())
    assert app.clipboard().image().pixelColor(8,8).name()=='#000000'
    assert not app.clipboard().mimeData().hasUrls()
    window.tabs.clear(); window.close()


def test_selection_move_resize_duplicate_delete(app):
    w=Window(); w.show()
    d=Document(Image.new('RGBA',(400,300),'white'))
    d.commit([Shape('rect',((50,50),(120,120)))])
    w.add_document(d); app.processEvents()
    c=w.canvas(); c.resetTransform(); c.set_tool('select')
    item=c.items_by_index[0]; item.setSelected(True)
    item.setPos(10,20)
    # A real release commits transient Qt geometry to original-image coordinates.
    QTest.mouseRelease(c.viewport(),Qt.LeftButton,Qt.NoModifier,c.mapFromScene(85,95))
    assert d.shapes[0].points==((60,70),(130,140))
    c.items_by_index[0].setSelected(True)
    a=c.mapFromScene(130,140); b=c.mapFromScene(160,175)
    QTest.mousePress(c.viewport(),Qt.LeftButton,Qt.NoModifier,a)
    QTest.mouseMove(c.viewport(),b)
    QTest.mouseRelease(c.viewport(),Qt.LeftButton,Qt.NoModifier,b)
    assert d.shapes[0].points==((60,70),(160,175))
    c.items_by_index[0].setSelected(True)
    c.setFocus(); w.duplicate(); assert len(d.shapes)==2
    c.items_by_index[1].setSelected(True); w.delete(); assert len(d.shapes)==1
    w.tabs.clear(); w.close()


def test_brush_stroke_and_cancel(app):
    d=Document(Image.new('RGBA',(300,200),'white'))
    c=Canvas(d); c.resize(600,400); c.show(); app.processEvents()
    c.set_tool('brush')
    a=c.mapFromScene(30,30); b=c.mapFromScene(180,130)
    QTest.mousePress(c.viewport(),Qt.LeftButton,Qt.NoModifier,a)
    QTest.mouseMove(c.viewport(),b)
    QTest.mouseRelease(c.viewport(),Qt.LeftButton,Qt.NoModifier,b)
    assert len(d.shapes)==1 and d.shapes[0].kind=='brush'
    c.set_tool('rect')
    QTest.mousePress(c.viewport(),Qt.LeftButton,Qt.NoModifier,a)
    QTest.mouseMove(c.viewport(),b)
    c.cancel()
    QTest.mouseRelease(c.viewport(),Qt.LeftButton,Qt.NoModifier,b)
    assert len(d.shapes)==1
    c.close()


def test_socket_denied_workflow(app,monkeypatch,tmp_path):
    import socket
    from redact_studio.core import load_image,encode,write_unique
    def blocked(*a,**kw): raise AssertionError('Network use is forbidden')
    monkeypatch.setattr(socket,'socket',blocked)
    monkeypatch.setattr(socket,'create_connection',blocked)
    source=tmp_path/'synthetic.png'; Image.new('RGB',(64,48),'red').save(source)
    w=Window(); w.add_document(load_image(source))
    w.canvas().document.commit([Shape('rect',((0,0),(16,16)))])
    target=write_unique(encode(w.canvas().document),tmp_path/'safe.png',[source])
    assert Image.open(target).getpixel((4,4))==(0,0,0)
    w.tabs.clear(); w.close()


def test_batch_reports_success_failure_and_cancel(app,monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    w=Window()
    for name in ('One','Two','Three'):
        w.add_document(Document(Image.new('RGBA',(8,8),'red'),name=name))
    results=iter(['saved',None,OSError('synthetic failure')])
    def export(document):
        value=next(results)
        if isinstance(value,Exception): raise value
        return value
    messages=[]
    monkeypatch.setattr(w,'export_document',export)
    monkeypatch.setattr(QMessageBox,'information',lambda parent,title,text:messages.append(text))
    w.batch()
    assert messages==['Saved: 1\nFailed: 1\nCancelled: 1']
    w.tabs.clear(); w.close()


def test_review_fails_closed_on_render_error(app,monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    import redact_studio.window as module
    d=Document(Image.new('RGBA',(8,8),'red'))
    defaults={'format':'PNG','suffix':'_REDACTED','directory':'','quality':95,'compression':6}
    review=Review(d,defaults)
    assert 'NO redactions' in review.confirm.text()
    review.accept(); assert review.result()!=QDialog.Accepted
    review.confirm.setChecked(True)
    def fail(*a,**kw): raise MemoryError('Synthetic allocation failure')
    monkeypatch.setattr(module,'encode',fail)
    monkeypatch.setattr(QMessageBox,'warning',lambda *a,**kw:QMessageBox.Ok)
    review.format.setCurrentText('WEBP')
    assert review.data is None
    assert not review.confirm.isEnabled()
    review.accept(); assert review.result()!=QDialog.Accepted
    review.close()


def test_start_screen_and_application_icon(app):
    from redact_studio.resources import asset
    from PIL import Image
    window = Window()
    assert not window.windowIcon().isNull()
    assert window.workspace.currentIndex() == 0
    window.add_document(Document(Image.new('RGBA',(16,16),'white')))
    assert window.workspace.currentIndex() == 1
    window.tabs.clear()
    assert window.workspace.currentIndex() == 0
    with Image.open(asset('app.ico')) as icon:
        assert (16,16) in icon.ico.sizes()
        assert (256,256) in icon.ico.sizes()
    window.close()


@pytest.mark.parametrize('custom_folder', [False, True])
def test_image_review_uses_source_folder_or_explicit_preference(app, tmp_path, custom_folder):
    from pathlib import Path
    from redact_studio.core import load_image
    source_folder = tmp_path/'imports'; source_folder.mkdir()
    source = source_folder/'example.png'
    Image.new('RGB',(16,16),'red').save(source)
    original = source.read_bytes()
    override = tmp_path/'chosen'
    defaults = {'format':'PNG','suffix':'_REDACTED','directory':str(override) if custom_folder else '',
                'quality':95,'compression':6}
    review = Review(load_image(source), defaults)
    expected_folder = override if custom_folder else source_folder
    assert Path(review.destination.text()) == expected_folder/'example_REDACTED.png'
    review.format.setCurrentText('JPEG')
    assert Path(review.destination.text()) == expected_folder/'example_REDACTED.jpg'
    assert source.read_bytes() == original
    review.close()


def test_clipboard_review_retains_home_fallback(app):
    from pathlib import Path
    defaults = {'format':'PNG','suffix':'_REDACTED','directory':'','quality':95,'compression':6}
    review = Review(Document(Image.new('RGBA',(8,8),'white')), defaults)
    assert Path(review.destination.text()) == Path.home()/'Clipboard_REDACTED.png'
    review.close()
