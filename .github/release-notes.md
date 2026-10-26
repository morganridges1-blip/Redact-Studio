Portable Windows application for manually redacting images and PDFs. Python installation is not required.

Download **RedactStudio-Windows.zip** below, extract the entire ZIP, then open `RedactStudio/RedactStudio.exe`. Keep the `_internal` folder with the executable. The automatically generated **Source code** archives contain source files, not the Windows application.

Features include rectangle and freehand redaction, image exports, image-only PDF exports, whole-document PDF review, configurable PDF resolution, and dark/light themes. Exports default to the imported file's folder unless an export folder is configured.

The executable is **unsigned** and may trigger Windows SmartScreen. Follow your organisation's software approval policy. `SHA256SUMS.txt` provides the ZIP's checksum for download integrity; it is not a code signature.

Processing is local. Review every exported page carefully: the application does not automatically identify confidential content. Original files remain on disk. Windows clipboard history, cloud-synchronised folders, backups and operating-system behaviour are outside the application's control. This release has not received independent security certification. See [SECURITY.md](https://github.com/morganridges1-blip/Redact-Studio/blob/main/SECURITY.md) for data-handling limits.

Known review limitation: a redaction moved completely outside an image can still count as a redaction. A count alone does not establish that content is covered; inspect the actual exported output.

Distributed under GPLv3 with the bundled dependencies' licence notices.
