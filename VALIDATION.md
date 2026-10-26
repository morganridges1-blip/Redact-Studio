# Validation record

Executed in the Linux cloud environment on 26 October 2026, with Python 3.12.14, Pillow 12.2.0, PySide6 6.10.2, pytest 9.0.2 and PyInstaller 6.19.0. No user images or real personal information were used.

| Check | Result |
| --- | --- |
| Dependency installation and repeated installation from requirements-dev.txt | Passed |
| pip check | Passed; no broken requirements |
| Full pytest suite | **47 passed**, no failures or skips |
| GUI tests with QT_SCALE_FACTOR=2 | **12 passed**, no failures or skips |
| Source application --self-test, offscreen | Passed, exit 0 |
| PyInstaller onedir build on Linux using supplied spec | Passed |
| Frozen Linux application --self-test, offscreen | Passed, exit 0 |
| Visual inspection of synthetic offscreen editor screenshot | Performed |
| Windows executable build / execution | **Passed on GitHub Windows runner**; packaged self-test exit 0 |
| Interactive Windows 11 / physical high-DPI monitors / native clipboard history | **Not run** |
| Independent external metadata utility / OS-level traffic observation | **Not run**; independent container parsers and Python socket-denied smoke test ran |

The 47 tests cover rectangle and continuous brush replacement, overlaps, boundary rounding/clipping, transparency flattening, geometry-only history, orientation, supported input modes, corrupt/multi-frame/oversized input rejection, source-byte and mtime integrity, filename collisions, source/symlink destination protection, cleanup after an injected write failure, and unknown-shape rejection. They also cover preview/encoded-pixel equality, redaction placement from 10–800% zoom, selection/movement/resizing, duplicate/delete, brush cancellation, independent document histories, clipboard pixel conversion, batch success/failure/cancel summaries, mandatory no-region acknowledgement and fail-closed preview rendering.

Metadata fixtures exercise GPS, camera/author/date/comment fields, PNG text/XMP, WebP XMP, JPEG XMP/IPTC/comment payloads, and a real EXIF IFD1 containing a JPEG thumbnail. PNG, JPEG and WebP outputs are independently parsed to check container structures and tested for absence of inherited payloads. Counterfactual tests change source pixels solely under a rectangle and verify identical complete output bytes in each export format.

Qt offscreen runs emit font-cache and unsupported-size-hint diagnostics from the headless platform. The source and packaged self-tests still return exit status 0. These diagnostics contain no image data.

The first Windows CI run reached 46 passing tests and failed the static privacy test because `Path.read_text()` used Windows CP1252 for a UTF-8 source file. The test now explicitly reads UTF-8; no assertion was disabled. [Windows CI run #2](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40305162812), for commit `d534ec5`, subsequently passed the test step, PyInstaller build, frozen-application self-test and artifact upload. The test suite has 47 cases. The Windows PowerShell build script itself has not been separately executed.

The uploaded `RedactStudio-Windows` artifact is 52.8 MB and contains the executable plus its required libraries. GitHub reports artifact SHA-256 `008ea83361220904f109b894f940265b5886d492e119d24ae30283fb7ba8130f`. Interactive Windows 11 testing, security certification, external security audit and code signing remain outstanding. Complete the Windows checklist in SECURITY.md before organisational deployment.

Reusable cloud install_script and start_skill were saved to the environment draft. They reproduce dependency installation, source tests and headless startup; saving the draft does not publish it or establish restoration in a new task. At initial validation, source files were uncommitted in the originally empty Finance-Tracker checkout. The user subsequently corrected the destination to morganridges1-blip/Redact-Studio. The application was transferred to /workspace/Redact-Studio, retaining that repository’s existing licence and README description, and all 47 tests passed again. Refer to Git history for the current commit status.
