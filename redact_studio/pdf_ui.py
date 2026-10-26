"""PDF page editing and mandatory whole-document export review."""
import math
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QIcon, QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSpinBox, QDialog, QLineEdit, QFileDialog, QScrollArea,
    QCheckBox, QDialogButtonBox, QMessageBox, QListWidget, QListWidgetItem, QTabWidget, QAbstractItemView)

from .canvas import Canvas, pixmap
from .core import ImageError
from .pdf import PDF_DPI, encode_pdf, preview_pdf, preview_pdf_pages
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
        self.data = None
        self.setWindowTitle('Review and export PDF')
        self.resize(1040, 800)
        layout = QVBoxLayout(self)
        self.summary = QLabel()
        layout.addWidget(self.summary)
        layout.addWidget(QLabel('PDF • Image-only pages • Metadata: Automatically stripped'))
        self.destination = QLineEdit(str(Path(defaults['directory'] or Path.home()) /
                                            (book.name+defaults['suffix']+'.pdf')))
        layout.addWidget(self.destination)
        choose = QPushButton('Choose PDF destination…')
        choose.clicked.connect(self.choose)
        layout.addWidget(choose)
        layout.addWidget(QLabel('Scroll through all pages below. Double-click a page to inspect it at full resolution.'))
        self.views = QTabWidget()
        self.overview = QListWidget()
        self.overview.setViewMode(QListWidget.IconMode)
        self.overview.setIconSize(QSize(180, 240))
        self.overview.setGridSize(QSize(215, 285))
        self.overview.setResizeMode(QListWidget.Adjust)
        self.overview.setMovement(QListWidget.Static)
        self.overview.setSelectionMode(QAbstractItemView.SingleSelection)
        self.overview.setWordWrap(True)
        self.overview.itemDoubleClicked.connect(self.open_detail)
        self.views.addTab(self.overview, 'All pages')
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        navigation = QHBoxLayout()
        previous = QPushButton('Previous')
        following = QPushButton('Next')
        self.number = QSpinBox()
        self.number.setRange(1, len(book.pages))
        self.number.setPrefix('Page ')
        self.number.setSuffix(f' of {len(book.pages)}')
        previous.clicked.connect(lambda: self.number.setValue(self.number.value()-1))
        following.clicked.connect(lambda: self.number.setValue(self.number.value()+1))
        navigation.addWidget(previous)
        navigation.addWidget(self.number)
        navigation.addWidget(following)
        detail_layout.addLayout(navigation)
        self.image_label = QLabel('Choose a page from All pages to inspect the exported pixels.')
        self.image_label.setAlignment(Qt.AlignCenter)
        scroll = QScrollArea()
        scroll.setWidget(self.image_label)
        scroll.setWidgetResizable(True)
        detail_layout.addWidget(scroll)
        self.views.addTab(detail, 'Page detail')
        self.views.currentChanged.connect(self.detail_tab)
        layout.addWidget(self.views, 1)
        explanation = QLabel('Review the complete document before exporting. Redact Studio does not identify confidential information automatically. '
                             'Output contains only sanitised page images: searchable text, links, forms, attachments and accessibility tags are removed.')
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.unredacted = [i+1 for i, page in enumerate(book.pages) if not page.shapes]
        label = f'I reviewed the entire PDF and approve export of all {len(book.pages)} pages.'
        if self.unredacted:
            label += f' This includes {len(self.unredacted)} pages with NO redactions.'
        self.confirm = QCheckBox(label)
        self.confirm.toggled.connect(self.update_confirmation)
        layout.addWidget(self.confirm)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.save_button = buttons.button(QDialogButtonBox.Save)
        self.save_button.setText('Export PDF')
        self.save_button.setEnabled(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.number.valueChanged.connect(self.show_page)
        try:
            self.data = pixel_work(self, lambda: encode_pdf(book), 'Sanitising all PDF pages…')
            thumbnails = pixel_work(self, lambda: preview_pdf_pages(self.data), 'Preparing all-page PDF overview…')
            if len(thumbnails) != len(book.pages):
                raise ImageError('Incomplete PDF overview.')
            for index, image in enumerate(thumbnails):
                count = len(book.pages[index].shapes)
                text = f'Page {index+1}\n{count} redaction{"s" if count != 1 else ""}' if count else f'Page {index+1}\nNO redactions'
                item = QListWidgetItem(QIcon(pixmap(image)), text)
                item.setData(Qt.UserRole, index)
                item.setToolTip(f'Page {index+1}: double-click for full-resolution review')
                if not count:
                    item.setForeground(QColor('#d99000'))
                self.overview.addItem(item)
            redactions = sum(len(page.shapes) for page in book.pages)
            summary = f'{len(book.pages)} pages • {redactions} redactions • {PDF_DPI} DPI'
            if self.unredacted:
                summary += ' • No redactions on pages: ' + ', '.join(map(str, self.unredacted))
            self.summary.setText(summary)
            self.summary.setWordWrap(True)
        except Exception:
            self.fail()

    def fail(self):
        self.data = None
        self.confirm.setChecked(False)
        self.confirm.setEnabled(False)
        self.save_button.setEnabled(False)
        self.overview.clear()
        self.image_label.clear()
        self.summary.setText('PDF rendering failed. Export is disabled; no file was saved.')
        QMessageBox.warning(self, 'PDF review stopped', 'The PDF could not be rendered safely. Check available memory and the document.')

    def choose(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Export sanitised PDF', self.destination.text(),
                                             'PDF (*.pdf)', options=QFileDialog.DontConfirmOverwrite)
        if path:
            self.destination.setText(path)

    def open_detail(self, item):
        self.number.blockSignals(True)
        self.number.setValue(item.data(Qt.UserRole)+1)
        self.number.blockSignals(False)
        self.show_page()

    def detail_tab(self, index):
        if index == 1 and self.data is not None:
            self.show_page()

    def show_page(self, *args):
        if self.data is None:
            return
        try:
            index = self.number.value()-1
            self.preview_image = pixel_work(self, lambda: preview_pdf(self.data, index), 'Opening exported PDF page for review…')
            self.image_label.setPixmap(pixmap(self.preview_image))
            self.image_label.setMinimumSize(*self.preview_image.size)
            self.views.blockSignals(True)
            self.views.setCurrentIndex(1)
            self.views.blockSignals(False)
        except Exception:
            self.fail()

    def update_confirmation(self, *args):
        self.save_button.setEnabled(self.data is not None and self.confirm.isChecked())

    def accept(self):
        if self.data is not None and self.confirm.isChecked() and self.destination.text().strip():
            super().accept()
