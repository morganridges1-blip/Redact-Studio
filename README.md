# Redact-Studio
Securely redact information from images, overwriting the pixels and deletion of metadata

Native Python / Qt desktop editor for manual image redaction and mandatory metadata stripping. Processing uses local, deterministic Pillow operations. The application contains no AI, machine learning, OCR, HTTP client, telemetry or upload feature.

## Download the Windows executable

**Security update:** Pillow is now **13.0.0**, fixing the reported Pillow advisories. Download the rebuilt **[RedactStudio-Windows ZIP](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40307502583/artifacts/12643422335)** (52.9 MB) while signed into GitHub, or open the [successful security-update run](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40307502583) and find **Artifacts**. The Windows tests and packaged-application self-test passed. See [DEPENDENCY_SECURITY.md](DEPENDENCY_SECURITY.md) for the advisory review.

**Replace the entire old application folder, including `_internal`.** The original run #2 executable and libraries contain the affected Pillow version and are superseded.

Extract the complete ZIP into a folder, then double-click `RedactStudio.exe`. Keep the `_internal` folder beside it; this is a portable application folder, not a single self-contained executable. Python does not need to be installed on the destination PC. The executable is unsigned. Interactive Windows 11 desktop acceptance testing remains outstanding.

## Run from source

Requires Python 3.12+ and a desktop session (Windows 11 is the deployment target).

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python main.py
```

On Linux/macOS use `python3 -m venv .venv` and `.venv/bin/python` instead. Installation/building downloads dependencies; installed application operation requires no Internet access. The prepared cloud environment uses `/workspace/redact-venv/bin/python`. Its headless session can run tests with `QT_QPA_PLATFORM=offscreen`; it does not provide a Windows desktop.

## Edit and export

- Open, add, paste or drop PNG, JPEG, BMP, single-frame TIFF or WebP images. Each tab has independent edits and up to 100 undo steps. Multi-frame/animated inputs are explicitly rejected rather than silently discarding frames.
- Rectangle (`R`): drag over information. Freehand (`B`): paint continuous strokes; diameter is measured in original image pixels. Choose a solid colour in the sidebar; alpha is never supported.
- Selection (`V`): click or rubber-band select, Ctrl/Shift-click multiple regions, drag to move. Drag within 14 display pixels of a selected rectangle’s bottom-right corner to resize. The properties list also selects regions. Delete removes selections; Ctrl+D duplicates them.
- Remove Redaction deletes a clicked region. Pan (`H`), middle-drag or Space+drag moves the viewport. Wheel zoom anchors at the cursor. Zoom is constrained to 10–800%.
- Ctrl+Z undoes; Ctrl+Y or Ctrl+Shift+Z redoes. Esc cancels an active drawing/resizing operation. Geometry is stored in original-image coordinates, not display coordinates.
- Ctrl+0 fits the image; Ctrl+1 displays actual size. Ctrl+O opens; Ctrl+V pastes; Ctrl+S / Ctrl+Shift+S opens export review.
- Preview/Export shows **decoded final export bytes at 1:1**, in a scrollable view. Review the entire image, choose a destination and explicitly confirm. Changing format resets confirmation. PNG is the default; WebP is lossless. JPEG expands coverage to full 8×8 compression blocks and disables chroma subsampling. Review this larger coverage before saving.
- Batch Export reviews every tab separately and reports saved, failed and cancelled counts. Images with zero redactions require an explicit metadata-only review acknowledgement. Files never silently pass as manually redacted.
- Copy Redacted Image (Ctrl+Shift+C) uses reviewed, sanitised output pixels only and displays a Windows clipboard history/synchronisation warning. The review dialog's Save button confirms the image; clipboard copying does not save a file.
- Settings offers dark/light appearance, default tool, current sidebar colour/brush defaults, format, destination, suffix, PNG compression and JPEG quality. Only these preferences persist; document paths, image pixels and editing histories are not saved as application preferences.

Default filenames use `OriginalFilename_REDACTED.png`. Existing names receive `_1`, `_2`, etc. All open source paths are protected and files are created exclusively; no existing file is overwritten.

## Security model

The importer decodes and applies EXIF orientation, then creates a fresh RGBA image from pixels. It does not retain inherited metadata on that image. Editing overlays are separate geometry. Export creates a new opaque RGB buffer, flattens transparency against white, overwrites masked pixels and re-encodes a fresh image without EXIF, XMP, IPTC, thumbnails, ICC profiles or source chunks. No original bytes, layers or metadata dictionaries are copied to output encoders. See [SECURITY.md](SECURITY.md) for exact guarantees and limitations.

PNG and WebP are lossless. JPEG's 8×8 block expansion ensures covered source pixels cannot influence the output through a shared compression block; JPEG can approximate custom solid colours. Image quality outside redactions is subject to JPEG compression. Source colour profiles are discarded, so some colours may differ from colour-managed viewers.

No unredacted temporary image is created. Export writes sanitised bytes to a newly created destination and removes that file on handled write failures. Creation and write errors stop the operation. Source files are opened read-only. A crash/power loss can leave an incomplete sanitised output; this is not reported as success. Normal newly generated filesystem timestamps remain.

Image limit: 24 million pixels each; open-document budget: 48 million pixels. Pixel import, rendering and saving run on a worker thread with modal progress to prevent concurrent edits. Qt scene construction/clipboard conversion still uses the UI thread. Memory availability below these limits can still cause a safely reported failure. Close tabs to free their retained images/history. There is no autosave or project-file format.

## Tests

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python -m pytest -q
$env:QT_SCALE_FACTOR = '2'
.\.venv\Scripts\python -m pytest tests/test_gui.py -q
.\.venv\Scripts\python main.py --self-test
```

Use `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q` on headless Linux. Tests use fictional synthetic content, independently parse output PNG/JPEG/WebP containers, compare redacted pixels and counterfactual source edits, exercise GUI mouse interactions, and deny Python socket creation during a workflow smoke test. This is evidence for the tested cases, not a security certification or proof about every decoder/OS.

## Windows executable

Run on **Windows 11 with Python 3.12**:

```powershell
powershell -ExecutionPolicy Bypass -File packaging/build-windows.ps1
.\dist\RedactStudio\RedactStudio.exe --self-test
.\dist\RedactStudio\RedactStudio.exe
```

The process does not request elevation. The build script installs dependencies, runs tests and packages an onedir application. Distribute the **entire** `dist/RedactStudio` folder, including Qt/Pillow libraries and their licence notices. Do not distribute just the executable. Build-time PowerShell execution policy override applies to this command only. No installer or administrator privileges are needed for normal use.

`.github/workflows/windows.yml` also tests and packages on a Windows runner and uploads a downloadable artifact when run in GitHub. The workflow succeeded in the [security-update run](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40307502583): Windows source tests, executable packaging and the frozen-application self-test all passed. PyInstaller does not cross-compile Windows executables on Linux; this executable was built on GitHub’s Windows runner. Interactive Windows 11 acceptance testing is still required.

Before workplace deployment, run the Windows acceptance checklist in [SECURITY.md](SECURITY.md), review dependency licences and decide whether your organisation requires executable signing. Unsigned executables can trigger SmartScreen. See [VALIDATION.md](VALIDATION.md) for executed checks and outstanding validation.
