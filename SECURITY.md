# Security and governance review

## Boundaries

Redact Studio performs manual redaction. It does not identify sensitive text or guarantee that a user selected every confidential region. Review the complete decoded output before confirming. Blur and pixelation are not implemented as redaction methods.

Security-sensitive code is in `redact_studio/core.py`: input decoding, pixel masks, fresh-buffer encoding and exclusive destination writes. `window.py` requires explicit export review and refuses export after rendering failures. `canvas.py` stores geometry in original-image coordinates; Qt editing overlays never enter export encoding. Unknown shape types fail closed. The source file is never opened for writing. Rectangle bounds round outward; brush strokes connect sampled points and add round endpoint coverage.

Metadata stripping is mandatory, including for zero-region images and clipboard output. Output containers may have encoder-generated **structural** data: PNG IHDR/IDAT/IEND, JPEG JFIF APP0 plus quantisation/Huffman/frame/scan markers, and WebP RIFF/VP8L structures. These do not come from source metadata. No output format preserves original profiles, comments, orientation tags, thumbnails or application payloads. Filesystem ownership/timestamps generated for a new file remain.

JPEG block expansion precedes encoding with 4:4:4 chroma. This prevents source data beneath the original mask from affecting output. It can redact more than the selected geometry. Lossless PNG is recommended for predictable coverage and colour fidelity. Test suites inspect container tags using independently implemented parsers, rather than only Pillow metadata APIs.

Only pixel buffers and edit geometry are retained in memory. Undo history stores geometry, never a full image per step. No application image cache, logs, source thumbnails or recent-file list is written. QSettings stores only explicit defaults. Qt/Windows file dialogs, the OS clipboard, swap, hibernation, crash dumps, filesystem indexing, antivirus and external backup/sync software are outside this guarantee. Memory is not securely zeroised. Ordinary deletion does not imply forensic erasure. Work on approved local storage and apply workplace OS controls.

Export uses exclusive file creation and rejects known source destinations, including resolved symlink aliases. Existing files are not overwritten. On a handled write or fsync failure the partial sanitised file is removed. It is possible for a process crash or power failure to leave partial sanitised output. Concurrent malicious filesystem manipulation is outside the threat model; select a trusted destination directory.

Malformed images are processed by Pillow's native decoders; pinning versions is not a substitute for dependency vulnerability review. Images above 24 MP, unsupported formats and multi-frame images are rejected. Aggregate open-document budget is 48 MP. These bounds limit, but do not guarantee, memory availability. Source ICC profiles are discarded rather than interpreted or preserved. No OpenCV dependency is used.

## Network and dependency review

Application modules import only Python standard library, Pillow and PySide6. There are no AI/ML/OCR/network/telemetry application imports. PyInstaller explicitly excludes Qt Network, WebEngine, QML and Multimedia from the package. Python socket creation is denied during one automated source workflow; independent OS-level traffic observation and frozen Windows offline operation remain acceptance tasks. Tests do not claim to prove that third-party libraries or Windows never communicate.

Runtime dependency pins are in `requirements.txt`; testing and packaging pins are in `requirements-dev.txt`. Qt/PySide6 and Pillow contain native code and have third-party licence obligations. Keep library licence files in distributions and perform your organisation's dependency/security review before release. No credentials or remote APIs are required.

## Windows 11 acceptance checklist (not executed in this Linux task)

- Build and run the complete onedir package on a clean standard-user Windows 11 account, with network disconnected. Run `RedactStudio.exe --self-test`; verify exit code 0.
- Observe process traffic using approved OS tooling. Verify no application network connections while opening, editing, copying and exporting synthetic images.
- Test 100%, 150%, 200% DPI, multiple monitors, resize/move/select, cursor-centred zoom, pan, all keyboard shortcuts, native dialogs, drag/drop and clipboard round trip.
- Verify Windows clipboard history/cloud clipboard behaviour is understood and controlled. Copy output into a second image editor and inspect redacted pixels.
- Import PNG/JPEG/BMP/TIFF/WebP fixtures, rotated EXIF input, transparent input and files near the size budget. Exercise cancellation, corrupt metadata, low-memory and disk-full/permission cases.
- Independently inspect exported files using an approved metadata utility (for example ExifTool): no inherited GPS, EXIF, XMP, IPTC, ICC, comments or thumbnails. Verify orientation and pixel coverage in another image viewer.
- Test batch review, zero-redaction acknowledgement, filename collisions, source integrity, invalid directories and large-image responsiveness.
- Review dependency inventory/licences, code-signing requirements, deployment policy and source with the security/data-governance team. These tests are not a certification.

## PDF documents

PDF input is rasterised locally with PDFium at 200 DPI and exported through a fresh image-only PDF writer. No source PDF objects, text streams, metadata, attachments, actions, signatures or editable layers are copied. Review requires approval of every page, including explicit approval for pages without redactions. Encrypted PDFs and XFA forms are rejected. The source is retained in memory without unredacted temporary files. See [PDF_SUPPORT.md](PDF_SUPPORT.md) for limits, native renderer configuration and independent object/pixel checks. PDFium is a native parser and requires ongoing dependency security review.
