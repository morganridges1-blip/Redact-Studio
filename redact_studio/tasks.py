"""Run pixel work off the GUI thread while a modal dialog prevents edit races."""
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, QEventLoop, Qt
from PySide6.QtWidgets import QProgressDialog

class Signals(QObject):
    finished = Signal()

class Work(QRunnable):
    def __init__(self, operation):
        super().__init__()
        self.operation = operation
        self.signals = Signals()
        self.result = None
        self.error = None

    def run(self):
        try:
            self.result = self.operation()
        except Exception as error:
            self.error = error
        finally:
            self.signals.finished.emit()


def pixel_work(parent, operation, message):
    dialog = QProgressDialog(message, '', 0, 0, parent)
    dialog.setCancelButton(None)
    dialog.setWindowModality(Qt.ApplicationModal)
    dialog.setMinimumDuration(0)
    dialog.setWindowTitle('Local image processing')
    loop = QEventLoop()
    work = Work(operation)
    work.signals.finished.connect(loop.quit)
    dialog.show()
    QThreadPool.globalInstance().start(work)
    loop.exec()
    dialog.close()
    if work.error is not None:
        raise work.error
    return work.result
