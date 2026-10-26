# Validation record

Executed in the Linux cloud environment on 26 October 2026, with Python 3.12.14, Pillow 13.0.0, PySide6 6.10.2, pytest 9.0.3 and PyInstaller 6.19.0. No user images or real personal information were used.

| Check | Result |
| --- | --- |
| Dependency installation and repeated installation from requirements-dev.txt | Passed |
| pip check | Passed; no broken requirements |
| Full pytest suite | **48 passed**, no failures or skips |
| GUI tests with QT_SCALE_FACTOR=2 | **12 passed**, no failures or skips |
| Source application --self-test, offscreen | Passed, exit 0 |
| PyInstaller onedir build on Linux using supplied spec | Passed |
| Frozen Linux application --self-test, offscreen | Passed, exit 0 |
| Visual inspection of synthetic offscreen editor screenshot | Performed |
| Windows executable build / execution | **Passed on GitHub Windows runner**; packaged self-test exit 0 |
| Interactive Windows 11 / physical high-DPI monitors / native clipboard history | **Not run** |
| Independent external metadata utility / OS-level traffic observation | **Not run**; independent container parsers and Python socket-denied smoke test ran |

The 48 tests cover rectangle and continuous brush replacement, overlaps, boundary rounding/clipping, transparency flattening, geometry-only history, orientation, supported input modes, corrupt/multi-frame/oversized input rejection, source-byte and mtime integrity, filename collisions, source/symlink destination protection, cleanup after an injected write failure, and unknown-shape rejection. The security-update regression test also verifies an unsupported decoder cannot be invoked by a misleading file extension. They also cover preview/encoded-pixel equality, redaction placement from 10–800% zoom, selection/movement/resizing, duplicate/delete, brush cancellation, independent document histories, clipboard pixel conversion, batch success/failure/cancel summaries, mandatory no-region acknowledgement and fail-closed preview rendering.

Metadata fixtures exercise GPS, camera/author/date/comment fields, PNG text/XMP, WebP XMP, JPEG XMP/IPTC/comment payloads, and a real EXIF IFD1 containing a JPEG thumbnail. PNG, JPEG and WebP outputs are independently parsed to check container structures and tested for absence of inherited payloads. Counterfactual tests change source pixels solely under a rectangle and verify identical complete output bytes in each export format.

Qt offscreen runs emit font-cache and unsupported-size-hint diagnostics from the headless platform. The source and packaged self-tests still return exit status 0. These diagnostics contain no image data.

The first Windows CI run reached 46 passing tests and failed the static privacy test because `Path.read_text()` used Windows CP1252 for a UTF-8 source file. The test now explicitly reads UTF-8; no assertion was disabled. [Windows CI run #2](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40305162812), for commit `d534ec5`, subsequently passed the test step, PyInstaller build, frozen-application self-test and artifact upload. The test suite has 47 cases. The Windows PowerShell build script itself has not been separately executed.

The uploaded `RedactStudio-Windows` artifact is 52.8 MB and contains the executable plus its required libraries. GitHub reports artifact SHA-256 `008ea83361220904f109b894f940265b5886d492e119d24ae30283fb7ba8130f`. Interactive Windows 11 testing, security certification, external security audit and code signing remain outstanding. Complete the Windows checklist in SECURITY.md before organisational deployment.

Reusable cloud install_script and start_skill were saved to the environment draft. They reproduce dependency installation, source tests and headless startup; saving the draft does not publish it or establish restoration in a new task. At initial validation, source files were uncommitted in the originally empty Finance-Tracker checkout. The user subsequently corrected the destination to morganridges1-blip/Redact-Studio. The application was transferred to /workspace/Redact-Studio, retaining that repository’s existing licence and README description, and all 47 tests passed again. Refer to Git history for the current commit status.

## Patched dependency build

The original Pillow 12.2.0 package was superseded after a Dependabot review. The source and Linux frozen self-tests were rerun with Pillow 13.0.0, pytest 9.0.3 and pip 26.2.2. All 48 source tests and 12 GUI tests at 200% scaling passed. PyPI exact-version metadata returned no active advisories for the 15 installed Linux runtime/build/test packages; the dated report is in `packaging/dependency-audit-2026-10-26.json`. This is a check of known package advisories, not a certification of all native code.

The [patched Windows build](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40307502583), from commit `ad522f7`, passed source tests, packaging, the frozen-application self-test and artifact upload. The replacement artifact is 52.9 MB, SHA-256 `132bb03e32cf7b5a5cd33fd8a1eeed0a0c7cb3155aee1c40d7329be6b3451334`. Replace the original run #2 folder completely. GitHub controls Dependabot alert rescanning/closure; no alert was dismissed or suppressed.

## PDF implementation validation

The PDF implementation passes 64 tests on Linux, including 16 PDF tests. All 28 GUI/PDF tests also pass at 200% display scaling. The source and Linux packaged application self-tests cover PDF rendering, redaction and image-only PDF round trips; independent pypdf inspection validates object removal and lossless pixel data. The updated [Windows CI run](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40339494565), from commit `e29fa39`, passed all source tests, packaging, the packaged image/PDF self-test and artifact upload. See PDF_SUPPORT.md for functionality and limitations.

The PDF-capable Windows application artifact is **56.8 MB**, SHA-256 `f3d0bd673eb981118b90816ab3b34feae1093d12e5d79e42bf04d487796feb64`. [Download the application ZIP](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40339494565/artifacts/12659305310) and replace the entire old application folder. A fresh exact-version PyPI metadata check returned no active advisories for all 17 installed Linux runtime/build/test packages, including pypdfium2 and development-only pypdf. Interactive Windows 11 desktop acceptance testing remains outstanding.

## Whole-document PDF review

PDF export now shows an all-pages thumbnail overview with optional full-resolution inspection and one confirmation for the complete document. The source suite passes 66 tests; all 30 GUI/PDF tests also pass at 200% scaling. Regression checks cover single-confirmation export, explicit unredacted-page labels, sanitised output thumbnails and disabled export after missing thumbnails or preview failures. Manual visual inspection used synthetic PDF content. The [Windows build](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40342516885), from commit `fa91dcf`, passed all 66 tests, packaging, the frozen-application self-test and artifact upload. The replacement Windows ZIP is 56.9 MB, SHA-256 `50a9c86c51880be779ba70d2fc06a09e57292ef468e6ae9084ff57b44ee93168`. [Download the application](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40342516885/artifacts/12659657370).

## Higher PDF resolution and interface refresh

PDF rendering now defaults to 300 DPI, with explicit 200/300/400/600 DPI choices for newly opened documents. The resolution remains fixed per document; tests verify pixel dimensions, page size, preview/export equality and aligned redactions for each option. A native rendering test loads standard A4 at 600 DPI and verifies rejection of an oversized page. The PDF page budget is 48 MP, document rendering budget 400 MP, and cached open-document budget remains 48 MP. Source image limits remain unchanged.

The interface has a flat toolbar, simplified fixed sidebars, a branded start screen and dark/light styles. Native toolbar relief has been removed. Canvas image scaling uses smooth pixmap transformation. A multi-size ICO is embedded in the Windows executable, while Qt uses the packaged PNG for window/taskbar icons. The packaged self-test now fails if the application icon is missing. All 74 source tests pass; all 38 GUI/PDF tests also pass at 200% scaling. The source and Linux packaged self-tests pass, including the icon presence check. Dark/light editor and start-screen screenshots were visually inspected. The [Windows build](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40345377516), for commit `07ffba1`, passed all 74 tests, packaging, the packaged icon/image/PDF self-test and artifact upload. The new Windows artifact is 56.8 MB, SHA-256 `e82b45af6b6f90eaecf50c4a41843905cd3f649746bf1681d023937b852c11e9`. [Download the application](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40345377516/artifacts/12661187398).

## Source-folder export defaults

Image and PDF review now default the output path to the imported file’s parent folder. An explicit export-directory preference still wins, and clipboard imports retain the home-folder fallback. The full source suite passes 79 tests, including image/PDF destination checks and source integrity checks. The [Windows build](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40348143437), for commit `7aec459`, passed all 79 tests, packaging, the packaged self-test and artifact upload. Artifact ZIP SHA-256: `c75ada7ab40fcf36845388f57ce84023216243d062a168e57ae1ee205f625d02`. [Download the application](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40348143437/artifacts/12661539918).
