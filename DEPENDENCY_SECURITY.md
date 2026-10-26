# Dependency security update — 26 October 2026

The original application pinned Pillow 12.2.0. Dependabot identified the following five distinct advisories, reported against both requirements.txt and requirements-dev.txt (which includes requirements.txt). The published Pillow maintainer advisories identify **13.0.0** as the patched release for every item. requirements.txt now pins that release; the development requirements inherit the same pin.

| Advisory | Affected component |
| --- | --- |
| [GHSA-v9pv-5gc8-w2m6](https://github.com/python-pillow/Pillow/security/advisories/GHSA-v9pv-5gc8-w2m6) | Stale native image storage in multi-frame loaders |
| [GHSA-w889-685w-c8fh](https://github.com/python-pillow/Pillow/security/advisories/GHSA-w889-685w-c8fh) | Ghostscript argument injection |
| [GHSA-332p-7hrc-92wf](https://github.com/python-pillow/Pillow/security/advisories/GHSA-332p-7hrc-92wf) | TIFF in-memory writer heap overflow |
| [GHSA-8g5g-8vmr-9782](https://github.com/python-pillow/Pillow/security/advisories/GHSA-8g5g-8vmr-9782) | JPEG decoder heap overflow |
| [GHSA-5x8w-8jj5-q52h](https://github.com/python-pillow/Pillow/security/advisories/GHSA-5x8w-8jj5-q52h) | FlashPix JPEG decoder heap overflow |

Pillow 13.0.0 also addresses the bundled OpenJPEG advisory [GHSA-78g4-xqwv-q3g8](https://github.com/python-pillow/Pillow/security/advisories/GHSA-78g4-xqwv-q3g8). No application format restriction is used as a substitute for upgrading the vulnerable native library.

The importer now supplies Pillow's explicit `formats` allowlist when opening a source, restricting decoder selection to PNG/JPEG/BMP/TIFF/WebP **before** a decoder opens the file. Previously, the application checked the detected format only after Image.open(). A regression test supplies EPS content disguised with a PNG filename and verifies that the unapproved decoder is never invoked. Existing multi-frame input rejection remains enabled.

A review of installed package/version metadata from PyPI also identified advisories for development-only pytest 9.0.2 (fixed in 9.0.3) and the virtual environment's pip 25.0.1. The development requirements now pin pytest 9.0.3 and pip 26.2.2. Windows CI and the local build script upgrade pip before installing build dependencies. Neither pytest nor pip is an application runtime dependency or an application networking feature.

After updating, the full suite passes 48 tests and the GUI suite passes 12 tests at 200% scaling on Linux. Source startup self-test and pip check also pass. A fresh Windows executable must be built from the patched dependency pin; changing source requirements does not update an existing executable.

**Replace the original run #2 executable and its whole accompanying folder.** Do not combine a new executable with an old `_internal` directory: the Pillow native libraries are in that directory. Original Windows package run #2 is historical and superseded. The replacement Windows build and packaged self-test must succeed before distribution.

The [package metadata report](packaging/dependency-audit-2026-10-26.json) returned no active advisories for all 17 installed Linux runtime/build/test package versions after updating. This check uses PyPI's advisory data for the exact installed versions. It is a dated check of known published advisories, not a guarantee that all native libraries are free of vulnerabilities. GitHub controls when Dependabot rescans and closes alerts; this task does not dismiss or suppress alerts.

The [replacement Windows build](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40307502583) succeeded from commit `ad522f7`: source tests, packaging, packaged-application self-test and uploads all passed. Download the [patched application ZIP](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40307502583/artifacts/12643422335); artifact SHA-256 is `132bb03e32cf7b5a5cd33fd8a1eeed0a0c7cb3155aee1c40d7329be6b3451334`. The original artifact has not been updated in place.
