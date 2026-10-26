# Security and data handling

Redact Studio processes images and PDFs locally. It has no application upload, telemetry, AI, machine-learning or OCR functionality. It does not enforce a network block or control Windows synchronisation services.

## Exported copies

Selected image pixels are replaced with opaque colours before encoding. Export creates new files without copying inherited metadata. PDF export builds fresh image-only pages without source text layers, attachments, scripts or editable objects. Normal filenames, filesystem timestamps and format-required structural data remain.

Source files are opened read-only. Existing destination files are not overwritten. Originals remain unredacted and must retain their normal access and retention controls. Review the whole exported copy; the application does not automatically identify confidential information.

## Local storage and memory

Working pixels, original PDF bytes and editing histories are held in memory. The application does not intentionally write unredacted temporary image/PDF files, content logs or a recent-document list. Settings store explicit preferences, including a configured export folder. Export defaults to the source folder unless overridden in Settings.

Memory is not securely wiped. Windows clipboard history, cloud clipboard, file-picker history, page files, crash dumps, indexing, backups and synchronised folders can retain content outside the application's control. Clipboard copying displays a privacy notice. Use approved local storage and workstation controls appropriate to the data.

## Deployment limitations

The executable is unsigned. The application adds no encryption, authentication, rights management or enterprise audit trail. Pillow, Qt and PDFium contain native code and run with the user's privileges; input limits do not provide a decoder sandbox. Keep dependencies and the complete application folder updated, including `_internal` and its licence notices.

Automated tests are not independent security certification. Obtain your organisation's approval before processing highly confidential information. Do not publish confidential sample documents in repository issues or build artifacts.
