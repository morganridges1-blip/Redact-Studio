"""Asset paths shared by source and the PyInstaller application."""
from pathlib import Path
from PySide6.QtGui import QIcon


def asset(name):
    return Path(__file__).resolve().parent.parent / 'assets' / name


def app_icon():
    return QIcon(str(asset('app.png')))
