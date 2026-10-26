# Run from the repository root: pyinstaller --clean --noconfirm packaging/redact_studio.spec
from pathlib import Path
from PyInstaller.utils.hooks import copy_metadata
root = Path(SPECPATH).parent
licence_metadata = []
for package in ('Pillow', 'PySide6', 'PySide6_Essentials', 'PySide6_Addons', 'shiboken6', 'pypdfium2'):
    licence_metadata += copy_metadata(package)
analysis = Analysis(
    [str(root / 'main.py')], pathex=[str(root)], binaries=[], datas=licence_metadata + [(str(root / 'assets'), 'assets')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['PySide6.QtNetwork','PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets',
              'PySide6.QtQml','PySide6.QtQuick','PySide6.QtMultimedia','tkinter','pypdf'],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name='RedactStudio',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=True, icon=str(root / 'assets' / 'app.ico'))
collection = COLLECT(exe, analysis.binaries, analysis.datas, strip=False, upx=False,
                     name='RedactStudio')
