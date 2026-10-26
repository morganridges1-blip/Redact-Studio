"""Offline PDF rasterisation and a fresh, image-only PDF writer.

PDFium only reads/renders input. Export never copies PDF objects, streams or tags.
All native PDFium calls are serialised: PDFium is not thread-safe.
"""
from dataclasses import dataclass, field
from contextlib import closing
from io import BytesIO
from pathlib import Path
import math
import threading
import zlib

import pypdfium2 as pdfium
from PIL import Image

from .core import Document, ImageError, render

PDF_DPI = 300
PDF_RESOLUTIONS = (200, 300, 400, 600)
MAX_PDF_BYTES = 100 * 1024 * 1024
MAX_OPEN_PDF_BYTES = 200 * 1024 * 1024
MAX_PDF_PAGES = 100
MAX_PDF_PAGE_PIXELS = 48_000_000
MAX_PDF_TOTAL_PIXELS = 400_000_000
MAX_OUTPUT_BYTES = 256 * 1024 * 1024
_PDF_LOCK = threading.RLock()


@dataclass
class PdfBook:
    source_bytes: bytes = field(repr=False)
    source: Path | None
    name: str
    sizes: list
    pages: list = field(default_factory=list)
    dpi: int = PDF_DPI

    @property
    def shapes(self):
        return [shape for page in self.pages for shape in page.shapes]

    def raster(self, index):
        try:
            with _PDF_LOCK, pdfium.PdfDocument(self.source_bytes) as pdf:
                if pdf.get_formtype() in (2, 3):
                    raise ImageError('XFA PDF forms are not supported. Use a flattened PDF.')
                pdf.init_forms(config=pdfium.raw.FPDF_FORMFILLINFO(version=2, xfa_disabled=True))
                with closing(pdf[index]) as page:
                    with closing(page.render(scale=self.dpi / 72, draw_annots=True)) as bitmap:
                        pixels = bitmap.to_pil().convert('RGBA')
                        # convert() owns its pixel buffer independently of the native bitmap.
                        pixels.info.clear()
                        return pixels
        except ImageError:
            raise
        except Exception:
            raise ImageError('The PDF page could not be rendered safely.') from None

    def load_page(self, index, release_previous=True):
        if not 0 <= index < len(self.pages):
            raise ImageError('Invalid PDF page.')
        page = self.pages[index]
        if page.pixels is None:
            pixels = self.raster(index)
            # Only the current page stays cached; edits/history remain per page.
            if release_previous:
                for previous in self.pages:
                    previous.pixels = None
            page.pixels = pixels
        return page


def load_pdf(path, dpi=PDF_DPI):
    try:
        path = Path(path)
        with path.open('rb') as stream:
            data = stream.read(MAX_PDF_BYTES + 1)
        if len(data) > MAX_PDF_BYTES:
            raise ImageError('PDF exceeds the 100 MB input limit.')
        return pdf_from_bytes(data, path.resolve(), path.stem, dpi=dpi)
    except ImageError:
        raise
    except Exception:
        raise ImageError('PDF could not be opened safely. It may be damaged or password-protected.') from None


def pdf_from_bytes(data, source=None, name='PDF document', dpi=PDF_DPI):
    try:
        if dpi not in PDF_RESOLUTIONS:
            raise ImageError('Choose a supported PDF resolution: 200, 300, 400 or 600 DPI.')
        if len(data) > MAX_PDF_BYTES:
            raise ImageError('PDF exceeds the 100 MB input limit.')
        with _PDF_LOCK, pdfium.PdfDocument(data) as pdf:
            if pdfium.raw.FPDF_GetSecurityHandlerRevision(pdf) >= 0:
                raise ImageError('Encrypted PDFs are not supported. Open an unencrypted copy.')
            if not 1 <= len(pdf) <= MAX_PDF_PAGES:
                raise ImageError('PDF must contain between 1 and 100 pages.')
            if pdf.get_formtype() in (2, 3):
                raise ImageError('XFA PDF forms are not supported. Use a flattened PDF.')
            sizes = []
            total = 0
            for i in range(len(pdf)):
                with closing(pdf[i]) as page:
                    width, height = page.get_size()
                if not all(math.isfinite(v) and v > 0 for v in (width, height)):
                    raise ImageError('PDF has an invalid page size.')
                pixels = math.ceil(width * dpi / 72) * math.ceil(height * dpi / 72)
                if pixels > MAX_PDF_PAGE_PIXELS:
                    raise ImageError('A PDF page exceeds 48 megapixels at this resolution. Choose a lower PDF resolution in Settings and reopen it.')
                total += pixels
                sizes.append((width, height))
            if total > MAX_PDF_TOTAL_PIXELS:
                raise ImageError('PDF exceeds the total rendering budget. Choose a lower PDF resolution in Settings and reopen it.')
        book = PdfBook(data, source, name, sizes, dpi=dpi)
        book.pages = [Document(None, source, f'{name} — page {i+1}', pdf_book=book, page_index=i)
                      for i in range(len(sizes))]
        book.load_page(0)
        return book
    except ImageError:
        raise
    except Exception:
        raise ImageError('PDF could not be opened safely. It may be damaged or password-protected.') from None


def encode_pdf(book):
    """Build a new PDF from losslessly compressed sanitised RGB pixels only."""
    output = BytesIO()
    output.write(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0]

    def obj(number, body):
        if number != len(offsets):
            raise ImageError('Invalid PDF object sequence; export stopped.')
        offsets.append(output.tell())
        output.write(f'{number} 0 obj\n'.encode('ascii'))
        output.write(body)
        output.write(b'\nendobj\n')
        if output.tell() > MAX_OUTPUT_BYTES:
            raise ImageError('PDF output exceeds the 256 MB limit.')

    def stream(dictionary, data):
        return dictionary + f' /Length {len(data)} >>\nstream\n'.encode('ascii') + data + b'\nendstream'

    count = len(book.pages)
    if count != len(book.sizes) or count == 0:
        raise ImageError('Invalid PDF page collection; export stopped.')
    obj(1, b'<< /Type /Catalog /Pages 2 0 R >>')
    kids = ' '.join(f'{3+i*3} 0 R' for i in range(count))
    obj(2, f'<< /Type /Pages /Count {count} /Kids [{kids}] >>'.encode('ascii'))
    for index, (page, (width, height)) in enumerate(zip(book.pages, book.sizes)):
        pixels = page.pixels if page.pixels is not None else book.raster(index)
        # Transient document avoids changing the editor's cached page/history.
        clean = render(Document(pixels, shapes=list(page.shapes)))
        compressed = zlib.compress(clean.tobytes(), 6)
        number = 3 + index * 3
        obj(number, (f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width:.6f} {height:.6f}] '
                     f'/Resources << /XObject << /Im0 {number+1} 0 R >> >> '
                     f'/Contents {number+2} 0 R >>').encode('ascii'))
        header = (f'<< /Type /XObject /Subtype /Image /Width {clean.width} /Height {clean.height} '
                  '/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode').encode('ascii')
        obj(number+1, stream(header, compressed))
        commands = f'q\n{width:.6f} 0 0 {height:.6f} 0 0 cm\n/Im0 Do\nQ\n'.encode('ascii')
        obj(number+2, stream(b'<<', commands))
    xref = output.tell()
    output.write(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode('ascii'))
    for offset in offsets[1:]:
        output.write(f'{offset:010d} 00000 n \n'.encode('ascii'))
    output.write((f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n'
                  f'startxref\n{xref}\n%%EOF\n').encode('ascii'))
    return output.getvalue()


def preview_pdf(data, index, dpi=PDF_DPI):
    """Decode the actual exported PDF, not its editable input, for review."""
    with _PDF_LOCK, pdfium.PdfDocument(data) as pdf:
        with closing(pdf[index]) as page:
            with closing(page.render(scale=dpi / 72)) as bitmap:
                return bitmap.to_pil().convert('RGB').copy()


def preview_pdf_pages(data, max_size=240):
    """Bounded thumbnails of every actual output page for document review."""
    images = []
    with _PDF_LOCK, pdfium.PdfDocument(data) as pdf:
        for index in range(len(pdf)):
            with closing(pdf[index]) as page:
                width, height = page.get_size()
                scale = min(PDF_DPI / 72, max_size / max(width, height))
                with closing(page.render(scale=scale)) as bitmap:
                    images.append(bitmap.to_pil().convert('RGB').copy())
    return images
