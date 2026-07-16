"""
PDF text extraction. Handles text-native PDFs (the common case for
digitally-produced reports, manuals, and logs). Scanned/image-only PDFs
need OCR (PaddleOCR/EasyOCR) as a fallback -- not implemented yet, see
the TODO below; most industrial reports produced digitally (not scanned)
work fine through this path alone.
"""

from __future__ import annotations

from dataclasses import dataclass

import pdfplumber


@dataclass
class PageText:
    page_number: int
    text: str


@dataclass
class ExtractedDocument:
    source_path: str
    pages: list[PageText]

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text)


def extract_pdf_text(path: str) -> ExtractedDocument:
    pages: list[PageText] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append(PageText(page_number=i, text=text))

    doc = ExtractedDocument(source_path=path, pages=pages)

    if not doc.full_text.strip():
        # TODO: fall back to OCR (PaddleOCR/EasyOCR) here for scanned PDFs --
        # pdfplumber returns empty text for image-only pages.
        raise ValueError(
            f"No extractable text in {path} -- likely a scanned/image PDF. "
            "OCR fallback not yet implemented."
        )
    return doc


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """Simple sliding-window chunker for embedding. Good enough for MVP;
    swap for a structure-aware chunker (by section/heading) later."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks
