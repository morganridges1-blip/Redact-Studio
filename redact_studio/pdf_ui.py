"""PDF page editing and mandatory whole-document export review."""
import math
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSpinBox, QDialog, QLineEdit, QFileDialog, QScrollArea,
    QCheckBox, QDialogButtonBox, QMessageBox)

from .canvas import Canvas, pixmap
from .core import ImageError
from .pdf import PDF_DPI, encode_pdf, preview_pdf
from .tasks import pixel_work


class PdfEditor(QWidget):
    ready = Signal()

    def __init__(self, book, budget_check, parent=None):
        super().__init__(parent)
        self.book = book
        self.budget_check = budget_check
        self.index = 0
        self.selections = {}
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        navigation = QHBoxLayout()
        self.previous = QPushButton('Previous page')
        self.next = QPushButton('Next page')
        self.number = QSpinBox()
        self.number.setRange(1, len(book.pages))
        self.number.setPrefix('Page ')
        self.number.setSuffix(f' of {len(book.pages)}')
        navigation.addWidget(self.previous)
        navigation.addWidget(self.number)
        navigation.addWidget(self.next)
        navigation.addStretch()
        navigation.addWidget(QLabel(f'{PDF_DPI} DPI • Image-only PDF export'))
        self.layout.addLayout(navigation)
        self.canvas = Canvas(book.pages[0])
        self.layout.addWidget(self.canvas)
        self.previous.clicked.connect(lambda: self.number.setValue(self.index))
        self.next.clicked.connect(lambda: self.number.setValue(self.index + 2))
        self.number.valueChanged.connect(self.switch)
        self.update_navigation()

    @property
    def document(self):
        return self.canvas.document

    def update_navigation(self):
        self.previous.setEnabled(self.index > 0)
        self.next.setEnabled(self.index < len(self.book.pages) - 1)

    def switch(self, number):
        index = number - 1
        if index == self.index:
            return
        old = self.canvas
        try:
            width, height = self.book.sizes[index]
            required = math.ceil(width*PDF_DPI/72) * math.ceil(height*PDF_DPI/72)
            if not self.budget_check(required):
                raise ImageError('Close other documents before opening this PDF page.')
            old.cancel()
            self.selections[self.index] = old.selected()
            page = pixel_work(self, lambda: self.book.load_page(index, release_previous=False), 'Rendering PDF page locally…')
            new = Canvas(page)
            new.color, new.brush = old.color, old.brush
            new.set_tool(old.tool)
            new.rebuild(self.selections.get(index, ()))
            self.layout.replaceWidget(old, new)
            self.canvas = new
            self.index = index
            for previous_page in self.book.pages:
                if previous_page is not page:
                    previous_page.pixels = None
            old.hide()
            old.deleteLater()
            self.ready.emit()
            QTimer.singleShot(0, new.fit)
        except Exception:
            self.number.blockSignals(True)
            self.number.setValue(self.index+1)
            self.number.blockSignals(False)
            QMessageBox.warning(self, 'Page unavailable', 'The page could not be loaded safely. Check document limits and available memory.')
        self.update_navigation()


class PdfReview(QDialog):
    def __init__(self, book, defaults, parent=None):
        super().__init__(parent)
        self.book = book
        self.approved = set()
        self.data = None
        self.setWindowTitle('Review sanitised PDF — every page')
        self.resize(900, 760)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('PDF • Image-only pages • Metadata: Automatically stripped'))
        self.destination = QLineEdit(str(Path(defaults['directory'] or Path.home()) /
                                            (book.name+defaults['suffix']+'.pdf')))
        layout.addWidget(self.destination)
        choose = QPushButton('Choose PDF destination…')
        choose.clicked.connect(self.choose)
        layout.addWidget(choose)
        self.number = QSpinBox()
        self.number.setRange(1, len(book.pages))
        self.number.setPrefix('Review page ')
        self.number.setSuffix(f' of {len(book.pages)}')
        navigation = QHBoxLayout()
        previous = QPushButton('Previous')
        following = QPushButton('Next')
        previous.clicked.connect(lambda: self.number.setValue(self.number.value()-1))
        following.clicked.connect(lambda: self.number.setValue(self.number.value()+1))
        navigation.addWidget(previous)
        navigation.addWidget(self.number)
        navigation.addWidget(following)
        layout.addLayout(navigation)
        self.summary = QLabel()
        layout.addWidget(self.summary)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        scroll = QScrollArea()
        scroll.setWidget(self.image_label)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll, 1)
        explanation = QLabel('Review every page before exporting. Redact Studio does not identify confidential information automatically. '
                             'Output contains only sanitised page images: searchable text, links, forms, attachments and accessibility tags are removed.')
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.confirm = QCheckBox()
        self.confirm.toggled.connect(self.confirm_page)
        layout.addWidget(self.confirm)
        self.progress = QLabel()
        layout.addWidget(self.progress)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.save_button = buttons.button(QDialogButtonBox.Save)
        self.save_button.setEnabled(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.number.valueChanged.connect(self.show_page)
        try:
            self.data = pixel_work(self, lambda: encode_pdf(book), 'Sanitising all PDF pages…')
            self.show_page()
        except Exception:
            self.fail()

    def fail(self):
        self.data = None
        self.approved.clear()
        self.confirm.setEnabled(False)
        self.save_button.setEnabled(False)
        self.image_label.clear()
        self.summary.setText('PDF rendering failed. Export is disabled; no file was saved.')
        QMessageBox.warning(self, 'PDF review stopped', 'The PDF could not be rendered safely. Check available memory and the document.')

    def choose(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Export sanitised PDF', self.destination.text(),
                                             'PDF (*.pdf)', options=QFileDialog.DontConfirmOverwrite)
        if path:
            self.destination.setText(path)

    def show_page(self, *args):
        if self.data is None:
            return
        try:
            index = self.number.value()-1
            self.preview_image = pixel_work(self, lambda: preview_pdf(self.data, index), 'Opening exported PDF page for review…')
            self.image_label.setPixmap(pixmap(self.preview_image))
            self.image_label.setMinimumSize(*self.preview_image.size)
            page = self.book.pages[index]
            self.summary.setText(f'Page {index+1} • {len(page.shapes)} redactions • {PDF_DPI} DPI')
            label = f'I reviewed page {index+1}.'
            if not page.shapes:
                label += ' This page has NO redactions; I approve metadata-only sanitisation.'
            self.confirm.setText(label)
            self.confirm.blockSignals(True)
            self.confirm.setChecked(index in self.approved)
            self.confirm.blockSignals(False)
            self.update_progress()
        except Exception:
            self.fail()

    def confirm_page(self, checked):
        index = self.number.value()-1
        if checked:
            self.approved.add(index)
        else:
            self.approved.discard(index)
        self.update_progress()

    def update_progress(self):
        self.progress.setText(f'{len(self.approved)} of {len(self.book.pages)} pages approved')
        self.save_button.setEnabled(self.data is not None and len(self.approved) == len(self.book.pages))

    def accept(self):
        if self.data is not None and len(self.approved) == len(self.book.pages) and self.destination.text().strip():
            super().accept()
