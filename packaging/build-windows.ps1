$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
py -3.12 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required.' }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip==26.2.2
if ($LASTEXITCODE -ne 0) { throw 'Installer upgrade failed.' }
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
$env:QT_QPA_PLATFORM = 'offscreen'
& .\.venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed. Build stopped.' }
Remove-Item Env:QT_QPA_PLATFORM
& .\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm packaging/redact_studio.spec
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
$env:QT_QPA_PLATFORM = 'offscreen'
$smoke = Start-Process -FilePath '.\dist\RedactStudio\RedactStudio.exe' -ArgumentList '--self-test' -Wait -PassThru
Remove-Item Env:QT_QPA_PLATFORM
if ($smoke.ExitCode -ne 0) { throw 'Packaged application self-test failed.' }
Write-Host 'Built dist\RedactStudio\RedactStudio.exe. Distribute the whole RedactStudio folder.'
