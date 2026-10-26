from pathlib import Path
from PIL import Image
from PySide6.QtCore import Qt, QTimer, QSettings
from PySide6.QtGui import QAction, QKeySequence, QColor, QImage
from PySide6.QtWidgets import (QApplication,QMainWindow,QToolBar,QDockWidget,QWidget,
 QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QListWidget,QAbstractItemView,QSpinBox,
 QColorDialog,QFileDialog,QMessageBox,QTabWidget,QDialog,QDialogButtonBox,QComboBox,
 QLineEdit,QFormLayout,QCheckBox,QScrollArea,QProgressDialog)
from .canvas import Canvas, pixmap
from .tasks import pixel_work
from .core import Document, ImageError, load_image, encode, decoded_preview, write_unique, MAX_PIXELS, MAX_DOCUMENT_PIXELS

WARNING = ('Please review the entire image before exporting. Redact Studio does not automatically '
 'identify confidential information. All selected regions will be permanently redacted, '
 'and original image metadata will be removed.')
PRIVACY = ('All image processing occurs locally. No AI, machine learning or OCR is used. '
 'No network access is required. Image metadata is stripped automatically on export. '
 'Original files are not modified. Windows creates normal filesystem timestamps for new files.')

class Review(QDialog):
    def __init__(self, document, defaults, parent=None):
        super().__init__(parent)
        self.document = document
        self.defaults = defaults
        self.setWindowTitle('Review sanitised output')
        self.resize(820,720)
        layout = QVBoxLayout(self)
        self.format = QComboBox()
        self.format.addItems(['PNG','JPEG','WEBP'])
        self.format.setCurrentText(defaults['format'])
        layout.addWidget(self.format)
        self.destination = QLineEdit()
        layout.addWidget(QLabel('Destination filename (existing names receive a unique suffix)'))
        layout.addWidget(self.destination)
        choose = QPushButton('Choose destination…')
        choose.clicked.connect(self.choose)
        layout.addWidget(choose)
        self.summary = QLabel()
        layout.addWidget(self.summary)
        layout.addWidget(QLabel('Metadata: Automatically stripped'))
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        scroll = QScrollArea()
        scroll.setWidget(self.image_label)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll,1)
        warning = QLabel(WARNING)
        warning.setWordWrap(True)
        layout.addWidget(warning)
        self.confirm = QCheckBox('I reviewed the entire output image.' if document.shapes else
                                 'This image has NO redactions. I reviewed it and approve metadata-only sanitisation.')
        layout.addWidget(self.confirm)
        buttons = QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setEnabled(False)
        self.confirm.toggled.connect(buttons.button(QDialogButtonBox.Save).setEnabled)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.format.currentTextChanged.connect(self.refresh)
        self.refresh()

    def accept(self):
        if self.data is not None and self.confirm.isChecked() and self.destination.text().strip():
            super().accept()

    def choose(self):
        path,_ = QFileDialog.getSaveFileName(self,'Export sanitised image',self.destination.text(),
                                           'Image files (*.png *.jpg *.webp)',options=QFileDialog.DontConfirmOverwrite)
        if path: self.destination.setText(path)

    def refresh(self):
        self.data = None
        self.confirm.setChecked(False)
        try:
            self._refresh()
            self.confirm.setEnabled(True)
        except Exception:
            self.confirm.setEnabled(False)
            self.image_label.clear()
            self.summary.setText('Output could not be rendered. Export is disabled.')
            QMessageBox.warning(self, 'Rendering stopped', 'Unable to render safely. Check available memory and the image. No file was saved.')

    def _refresh(self):
        fmt = self.format.currentText()
        extension = {'PNG':'png','JPEG':'jpg','WEBP':'webp'}[fmt]
        name = self.document.name+self.defaults['suffix']+'.'+extension
        self.destination.setText(str(Path(self.defaults['directory'] or Path.home())/name))
        self.data = pixel_work(self, lambda: encode(self.document,fmt,self.defaults['quality'],self.defaults['compression']), 'Rendering and sanitising output…')
        self.preview_image = decoded_preview(self.data)
        # Scrollable 1:1 output enables inspection without hiding small sensitive text.
        self.image_label.setPixmap(pixmap(self.preview_image))
        self.image_label.setMinimumSize(*self.preview_image.size)
        extra = ' • JPEG expands coverage to 8×8 blocks' if fmt == 'JPEG' else ''
        self.summary.setText(f'{len(self.document.shapes)} redactions • {self.document.pixels.width} × {self.document.pixels.height} • {fmt}{extra}')
        self.confirm.setChecked(False)

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Redact Studio')
        self.resize(1420,900)
        self.setAcceptDrops(True)
        self.preferences = QSettings('RedactStudio','RedactStudio')
        self.defaults = {'format':str(self.preferences.value('format','PNG')),
                         'directory':str(self.preferences.value('directory','')),
                         'suffix':str(self.preferences.value('suffix','_REDACTED')),
                         'quality':int(self.preferences.value('quality',95)),
                         'compression':int(self.preferences.value('compression',6))}
        self.color = str(self.preferences.value('color','#000000'))
        self.default_tool = str(self.preferences.value('tool','rect'))
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.sync)
        self.setCentralWidget(self.tabs)
        self.toolbar = QToolBar('Image operations')
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        self.actions = {}
        for name,shortcut,callback in [
            ('Open Image','Ctrl+O',self.open_files),('Paste Image','Ctrl+V',self.paste),
            ('Add Images','',self.open_files),('Undo','Ctrl+Z',lambda:self.history(False)),
            ('Redo','Ctrl+Y',lambda:self.history(True)),('Zoom In','Ctrl++',lambda:self.navigate('in')),
            ('Zoom Out','Ctrl+-',lambda:self.navigate('out')),('Fit to Window','Ctrl+0',lambda:self.navigate('fit')),
            ('Actual Size','Ctrl+1',lambda:self.navigate('actual')),('Preview','',self.export),
            ('Export','Ctrl+S',self.export)]:
            self.action(name,shortcut,callback,self.toolbar)
        menu = self.menuBar().addMenu('File')
        self.action('Export As','Ctrl+Shift+S',self.export,menu)
        self.action('Batch Export','',self.batch,menu)
        self.action('Copy Redacted Image','Ctrl+Shift+C',self.copy,menu)
        self.action('Settings','',self.settings,menu)
        edit = self.menuBar().addMenu('Edit')
        self.action('Redo alternate','Ctrl+Shift+Z',lambda:self.history(True),edit)
        self.action('Duplicate selection','Ctrl+D',self.duplicate,edit)
        self.action('Delete selection','Delete',self.delete,edit)
        self.action('Cancel Operation','Esc',lambda:self.canvas() and self.canvas().cancel(),edit)
        tools = QWidget()
        left = QVBoxLayout(tools)
        left.addWidget(QLabel('REDACTION TOOLS'))
        self.tool_buttons = {}
        for title,key,tool in [('Rectangle','R','rect'),('Freehand','B','brush'),('Selection','V','select'),
                               ('Remove Redaction','','remove'),('Pan','H','pan')]:
            button = QPushButton(title)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False,t=tool:self.tool(t))
            left.addWidget(button)
            self.tool_buttons[tool] = button
            self.action(title+' shortcut',key,lambda checked=False,t=tool:self.tool(t),edit)
        help_text = QLabel('Selection: drag to move.\nShift/Ctrl-click: multi-select.\nDrag a selected rectangle’s\nbottom-right corner to resize.\n\nWheel: zoom at cursor.\nSpace + drag / middle drag: pan.')
        help_text.setWordWrap(True)
        left.addWidget(help_text)
        left.addStretch()
        self.dock('Tools',tools,Qt.LeftDockWidgetArea)
        properties = QWidget()
        right = QVBoxLayout(properties)
        self.tool_label = QLabel('Open an image to begin')
        right.addWidget(self.tool_label)
        self.color_button = QPushButton('Colour: '+self.color)
        self.color_button.clicked.connect(self.choose_color)
        right.addWidget(self.color_button)
        right.addWidget(QLabel('Brush diameter (image pixels)'))
        self.brush = QSpinBox()
        self.brush.setRange(1,1000)
        self.brush.setValue(int(self.preferences.value('brush',24)))
        self.brush.valueChanged.connect(self.update_brush)
        right.addWidget(self.brush)
        self.count = QLabel('0 redactions')
        right.addWidget(self.count)
        self.regions = QListWidget()
        self.regions.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.regions.itemSelectionChanged.connect(self.select_regions)
        right.addWidget(self.regions)
        self.dimensions = QLabel('No selection')
        right.addWidget(self.dimensions)
        for label,callback in [('Delete selected',self.delete),('Duplicate selected',self.duplicate)]:
            b=QPushButton(label); b.clicked.connect(callback); right.addWidget(b)
        right.addWidget(QLabel('● Local processing\nMetadata stripped on every export'))
        self.dock('Redaction properties',properties,Qt.RightDockWidgetArea)
        self.apply_theme(str(self.preferences.value('theme','dark')))
        self.statusBar().showMessage('Ready • Local processing • Open or drop images')

    def action(self,name,shortcut,callback,container):
        action = QAction(name,self)
        if shortcut: action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(callback)
        container.addAction(action)
        self.actions[name]=action
        return action

    def dock(self,title,widget,area):
        dock=QDockWidget(title,self); dock.setWidget(widget); dock.setMinimumWidth(210)
        self.addDockWidget(area,dock)

    def canvas(self): return self.tabs.currentWidget()

    def guard(self,operation):
        try: return operation()
        except Exception:
            QMessageBox.warning(self,'Operation stopped','The operation could not be completed safely. Check the image, available memory, destination permissions and disk space. No original image was changed.')

    def total_pixels(self):
        return sum(self.tabs.widget(i).document.pixels.width*self.tabs.widget(i).document.pixels.height for i in range(self.tabs.count()))

    def add_document(self,document):
        if self.total_pixels()+document.pixels.width*document.pixels.height > MAX_DOCUMENT_PIXELS:
            raise ImageError('Close some images before opening more.')
        canvas=Canvas(document)
        canvas.color=self.color; canvas.brush=self.brush.value()
        canvas.set_tool(self.default_tool)
        canvas.changed.connect(self.sync)
        canvas.zoomed.connect(self.status)
        canvas.scene().selectionChanged.connect(self.selection_status)
        index=self.tabs.addTab(canvas,document.name)
        self.tabs.setCurrentIndex(index)
        QTimer.singleShot(0,canvas.fit)
        self.sync()

    def open_files(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Open images','','Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp)')
        self.import_paths(paths)

    def import_paths(self,paths):
        for path in paths:
            self.guard(lambda p=path:self.add_document(pixel_work(self,lambda:load_image(p),'Loading image locally…')))

    def paste(self):
        def operation():
            image=QApplication.clipboard().image()
            if image.isNull(): raise ImageError('Clipboard contains no image.')
            if image.width()*image.height()>MAX_PIXELS: raise ImageError('Clipboard image too large.')
            image=image.convertToFormat(QImage.Format_RGBA8888)
            raw=bytes(image.constBits())
            pixels=Image.frombytes('RGBA',(image.width(),image.height()),raw,'raw','RGBA',image.bytesPerLine())
            self.add_document(Document(pixels))
        self.guard(operation)

    def tool(self,tool):
        if self.text_editing(): return
        if self.canvas(): self.canvas().set_tool(tool)

    def text_editing(self):
        return isinstance(QApplication.focusWidget(),(QLineEdit,QSpinBox,QComboBox))

    def choose_color(self):
        color=QColorDialog.getColor(QColor(self.color),self,'Solid redaction colour')
        if color.isValid():
            self.color=color.name(); self.color_button.setText('Colour: '+self.color)
            if self.canvas(): self.canvas().color=self.color

    def update_brush(self,value):
        if self.canvas(): self.canvas().brush=value

    def sync(self,*args):
        if not hasattr(self,'regions'): return
        canvas=self.canvas()
        self.regions.blockSignals(True)
        self.regions.clear()
        if canvas:
            for i,s in enumerate(canvas.document.shapes): self.regions.addItem(f'{i+1:02d}  {"Rectangle" if s.kind=="rect" else "Brush stroke"}')
            for i in canvas.selected(): self.regions.item(i).setSelected(True)
            self.count.setText(f'{len(canvas.document.shapes)} redactions')
            self.tool_label.setText('Current tool: '+canvas.tool)
            for tool,b in self.tool_buttons.items(): b.setChecked(tool==canvas.tool)
            canvas.color=self.color; canvas.brush=self.brush.value()
        else: self.count.setText('0 redactions')
        self.regions.blockSignals(False)
        self.selection_status()
        self.status()

    def selection_status(self):
        if not hasattr(self,'dimensions'): return
        canvas=self.canvas()
        indices=canvas.selected() if canvas else []
        self.dimensions.setText('No selection' if not indices else f'{len(indices)} selected')
        if len(indices)==1:
            x0,y0,x1,y1=canvas.document.shapes[indices[0]].bounds
            self.dimensions.setText(f'{x1-x0:.1f} × {y1-y0:.1f} px')

    def select_regions(self):
        canvas=self.canvas()
        if canvas:
            indices={self.regions.row(i) for i in self.regions.selectedItems()}
            for i,item in enumerate(canvas.items_by_index): item.setSelected(i in indices)
            self.selection_status()

    def status(self):
        c=self.canvas()
        if c:
            d=c.document
            self.statusBar().showMessage(f'{d.source.name if d.source else d.name} • {d.pixels.width} × {d.pixels.height} • {c.transform().m11()*100:.0f}% • {len(d.shapes)} redactions • Local processing')

    def history(self,redo):
        if self.text_editing(): return
        c=self.canvas()
        if c:
            c.document.redo() if redo else c.document.undo()
            c.rebuild()

    def delete(self):
        if self.text_editing(): return
        c=self.canvas()
        if c:
            indices=c.selected()
            c.document.commit([s for i,s in enumerate(c.document.shapes) if i not in indices]); c.rebuild()

    def duplicate(self):
        if self.text_editing(): return
        c=self.canvas()
        if c:
            c.document.commit(c.document.shapes+[c.document.shapes[i].moved(10,10) for i in c.selected()]); c.rebuild()

    def navigate(self,operation):
        c=self.canvas()
        if not c: return
        if operation=='fit': c.fit()
        elif operation=='actual': c.resetTransform(); c.zoomed.emit()
        else: c.zoom(1.25 if operation=='in' else .8)

    def sources(self): return [self.tabs.widget(i).document.source for i in range(self.tabs.count())]

    def export_document(self,document):
        dialog=Review(document,self.defaults,self)
        if dialog.exec()!=QDialog.Accepted: return None
        fmt=dialog.format.currentText()
        extension={'PNG':'.png','JPEG':'.jpg','WEBP':'.webp'}[fmt]
        destination=Path(dialog.destination.text())
        if destination.suffix.lower()!=extension:
            destination=destination.with_suffix(extension)
        sources = self.sources()
        return pixel_work(self,lambda:write_unique(dialog.data,destination,sources),'Saving sanitised pixels…')

    def export(self):
        if self.canvas():
            result=self.guard(lambda:self.export_document(self.canvas().document))
            if result: QMessageBox.information(self,'Export complete','Sanitised copy saved. Metadata: Automatically stripped.')

    def batch(self):
        if not self.tabs.count(): return
        success=failed=skipped=0
        for i in range(self.tabs.count()):
            try:
                result=self.export_document(self.tabs.widget(i).document)
                if result: success+=1
                else: skipped+=1
            except Exception: failed+=1
        QMessageBox.information(self,'Batch summary',f'Saved: {success}\nFailed: {failed}\nCancelled: {skipped}')

    def copy(self):
        c=self.canvas()
        if not c: return
        def operation():
            dialog=Review(c.document,self.defaults,self)
            dialog.setWindowTitle('Review before copying to clipboard')
            if dialog.exec()!=QDialog.Accepted: return
            if QMessageBox.warning(self,'Clipboard privacy','Windows clipboard history or synchronisation may retain copied content outside this application’s control. Copy sanitised pixels?',QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes: return
            QApplication.clipboard().setImage(pixmap(dialog.preview_image).toImage())
        self.guard(operation)

    def close_tab(self,index):
        if QMessageBox.question(self,'Close image','Discard this image’s in-memory editing history?',QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes:
            widget=self.tabs.widget(index); self.tabs.removeTab(index); widget.deleteLater()

    def closeEvent(self,event):
        if self.tabs.count() and QMessageBox.question(self,'Exit','Close all images and discard in-memory editing history?',QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:
            event.ignore()
        else: event.accept()

    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self,event):
        self.import_paths([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()])

    def apply_theme(self,theme):
        self.theme=theme
        bg,fg,panel=('#202632','#edf0f7','#2c3443') if theme=='dark' else ('#f0f3f8','#172036','#ffffff')
        self.setStyleSheet(f'QWidget {{ background:{bg}; color:{fg}; font-size:13px; }} QToolBar,QMenuBar,QDockWidget {{ spacing:6px; }} QPushButton,QComboBox,QSpinBox,QLineEdit {{ background:{panel}; padding:7px; border:1px solid #6a7385; border-radius:4px; }} QPushButton:checked {{ background:#365ec8; color:white; }} QToolButton {{ padding:8px; }} QListWidget {{ background:{panel}; }} QStatusBar {{ padding:5px; }}')

    def settings(self):
        dialog=QDialog(self); dialog.setWindowTitle('Settings'); layout=QFormLayout(dialog)
        theme=QComboBox(); theme.addItems(['dark','light']); theme.setCurrentText(self.theme)
        fmt=QComboBox(); fmt.addItems(['PNG','JPEG','WEBP']); fmt.setCurrentText(self.defaults['format'])
        directory=QLineEdit(self.defaults['directory'])
        suffix=QLineEdit(self.defaults['suffix'])
        quality=QSpinBox(); quality.setRange(1,100); quality.setValue(self.defaults['quality'])
        compression=QSpinBox(); compression.setRange(0,9); compression.setValue(self.defaults['compression'])
        tool=QComboBox(); tool.addItems(['rect','brush','select','pan']); tool.setCurrentText(self.default_tool)
        for label,widget in [('Appearance',theme),('Default tool',tool),('Export format',fmt),('Export directory',directory),('Filename suffix',suffix),('JPEG quality',quality),('PNG compression',compression)]: layout.addRow(label,widget)
        label=QLabel(PRIVACY+'\nColour and brush defaults use the current sidebar values.'); label.setWordWrap(True); layout.addRow(label)
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); layout.addRow(buttons)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
        if dialog.exec()==QDialog.Accepted:
            self.defaults={'format':fmt.currentText(),'directory':directory.text(),'suffix':suffix.text(),'quality':quality.value(),'compression':compression.value()}
            self.default_tool=tool.currentText()
            self.apply_theme(theme.currentText())
            for key,value in {**self.defaults,'theme':self.theme,'tool':self.default_tool,'color':self.color,'brush':self.brush.value()}.items(): self.preferences.setValue(key,value)
