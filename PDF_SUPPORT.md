# PDF processing

Open a PDF with **Open Image / PDF**, **Add Files**, or drag and drop. Each PDF opens in one tab. Use Previous page, Next page, or the page-number control to navigate. Rectangle/freehand editing, selection, movement, resizing, duplication and undo/redo work on the current page. Every page retains its own geometry and editing history.

## Export

Exporting a PDF always creates a **new PDF containing all pages**, in their original order. Each page is rendered locally at **300 DPI by default**, redactions permanently replace the covered pixels, and sanitised RGB pixels are losslessly compressed into a new PDF image object. Page dimensions, visible crop and rotation are reflected in the rendered output. Choose 200, 300, 400 or 600 DPI in **File → Settings → PDF resolution (new PDFs)** before opening the document. The selected resolution is fixed for that document and used for editing, detailed review and export, so redaction coordinates remain aligned. Changing Settings affects newly opened PDFs only. This is not a vector-preserving conversion; higher DPI improves vector rendering but cannot restore detail missing from embedded low-resolution images.

Review shows all pages in a scrollable thumbnail overview decoded from the actual output PDF. Double-click any page for full-resolution inspection. A single confirmation approves the entire document; there are no individual page approvals. Pages without redactions are labelled in the overview and listed in the summary, and the document-level confirmation explicitly includes them. Batch Export treats each PDF as one document and uses the same whole-document review. Clipboard copying exports the current page as sanitised image pixels; it does not copy the source PDF.

**The result is an image-only PDF.** Searchable/selectable text, links, form fields, annotations as editable objects, attachments, JavaScript, accessibility tags, digital signatures, source thumbnails and inherited metadata are not copied. Visible standard form/annotation appearances are flattened into pixels where PDFium renders them. Existing signatures are not preserved or validated. Review visual output carefully, including forms and annotations, before saving. Image-only documents may be larger and lose accessibility/search features.

Original PDFs are never modified or overwritten. Filename collisions receive a unique suffix. The original source bytes are held in memory while editing so a subsequent disk-file change cannot silently change the document being redacted. There are no unredacted temporary PDF/page files.

## Limits

| Limit | Value |
| --- | --- |
| Input PDF size | 100 MB |
| Retained source bytes across open PDFs | 200 MB maximum |
| Pages | 100 maximum |
| Resolution | 300 DPI default; 200 / 300 / 400 / 600 DPI selectable |
| Rendered size per PDF page | 48 megapixels maximum |
| Rendered size across a PDF | 400 megapixels maximum |
| Output PDF size | 256 MB maximum |
| Open-document cached image budget | 48 megapixels |

Pages are rendered on demand; only the active page is retained as editable pixels for each PDF. All pages retain their small geometry/history records. Navigating/exporting temporarily needs additional working buffers. These limits reduce memory demands but do not guarantee sufficient memory on every computer. Large or complex PDFs may take time to render. Rendering/export errors stop the operation and disable export; a failed page is never silently omitted.

Encrypted/password-protected PDFs (including empty-password encryption), XFA forms, invalid files and documents exceeding these limits are rejected. Open an approved, unencrypted/flattened copy if needed. No password recovery or bypass is provided.

## Implementation and verification

- `redact_studio/pdf.py`: PDFium rasterisation, size/page preflight and a fresh image-only PDF writer. All PDFium calls are serialised because PDFium is not thread-safe. The form configuration disables XFA and supplies no JavaScript platform or action callbacks. Document/page JavaScript actions are never invoked.
- `redact_studio/pdf_ui.py`: page navigation, independent edit histories and all-page overview and a single whole-document approval.
- `pypdfium2==5.14.0`: runtime renderer with bundled PDFium. PyInstaller includes the native library and package licence metadata.
- `pypdf==6.21.2`: development-only, independent PDF inspection and synthetic fixture creation. It is excluded from the packaged application.

The new dependencies had no active advisories in their exact-version PyPI metadata when checked on 26 October 2026. That is a dated known-advisory check, not a security certification of the native parser.

Tests use synthetic PDFs with text, XMP/author metadata, attachments, JavaScript, annotations and form fields. Independent pypdf inspection checks that output contains only a fresh page tree, content instructions and sanitised image objects; image bytes match the redaction engine output. Tests also cover rotated/cropped pages, page order, physical size, lazy caching, separate histories, source preservation, encrypted/corrupt inputs, budgets, failed rendering, PDF export routing and whole-document approval, thumbnail completeness and full-resolution inspection. The packaged application self-test exercises PDFium import, PDF decoding, redaction and PDF re-encoding without using pypdf or writing unredacted temporary files.

The [Windows build](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40345377516) passed all 74 tests and the packaged PDF self-test. Download the [PDF-capable Windows application](https://github.com/morganridges1-blip/Redact-Studio/actions/runs/40345377516/artifacts/12661187398) and replace the full application folder.

Higher DPI uses more memory and may increase file size. Standard A4 at 600 DPI is supported within the page budget. Larger pages/documents may require 300 or 400 DPI; limit errors instruct you to choose a lower resolution and reopen. The application does not silently reduce export resolution.
