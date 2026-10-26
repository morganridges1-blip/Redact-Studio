"""Desktop entry point. --self-test exercises the installed/frozen application."""
import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from redact_studio.window import Window


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Redact Studio')
    app.setOrganizationName('RedactStudio')
    app.setStyle('Fusion')
    window = Window()
    window.show()
    if '--self-test' in sys.argv:
        def check():
            try:
                from PIL import Image
                from redact_studio.core import Document, Shape, encode, decoded_preview
                document = Document(Image.new('RGBA', (64, 48), 'red'), name='Synthetic self-test')
                document.commit([Shape('rect', ((0, 0), (24, 24)))])
                window.add_document(document)
                for fmt in ('PNG', 'JPEG', 'WEBP'):
                    output = decoded_preview(encode(document, fmt))
                    if output.size != (64, 48) or output.getpixel((8, 8)) != (0, 0, 0):
                        raise RuntimeError('Pixel verification failed')
                from redact_studio.pdf import PdfBook, encode_pdf, pdf_from_bytes, preview_pdf
                seed = PdfBook(b'', None, 'Synthetic PDF', [(72,54)], [document])
                pdf_data = encode_pdf(seed)
                book = pdf_from_bytes(pdf_data)
                window.add_document(book)
                book.pages[0].commit([Shape('rect', ((0,0),(50,50)))])
                pdf_output = encode_pdf(book)
                if preview_pdf(pdf_output,0).getpixel((10,10)) != (0,0,0):
                    raise RuntimeError('PDF pixel verification failed')
                window.tabs.clear()
                app.exit(0)
            except Exception:
                app.exit(1)
        QTimer.singleShot(0, check)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
