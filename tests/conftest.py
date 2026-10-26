import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('XDG_CONFIG_HOME','/tmp/redact-studio-test-config')
import pytest
from PySide6.QtWidgets import QApplication

@pytest.fixture(scope='session')
def app():
    instance=QApplication.instance() or QApplication([])
    yield instance
    instance.clipboard().clear()
    instance.processEvents()
