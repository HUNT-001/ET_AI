"""
PDF text extraction. Handles text-native PDFs (the common case for
digitally-produced reports, manuals, and logs) and falls back to OCR for
scanned/image-only pages when Tesseract is available.

OCR is an optional dependency: install the Tesseract binary and `pytesseract`
to enable it. Without them, scanned PDFs raise a clear error rather than
failing silently — the text-native path needs nothing extra.
"""

from __future__ import annotations

import os
import re
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


def extract_pdf_text(path: str, ocr: bool | None = None) -> ExtractedDocument:
    """Extract text per page. For pages with no embedded text (scanned images),
    fall back to OCR when it's available. `ocr=None` (default) auto-enables OCR
    if pytesseract is importable; pass ocr=False to force text-only."""
    use_ocr = _ocr_available() if ocr is None else ocr
    pages: list[PageText] = []
    ocr_pages = 0
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip() and use_ocr:
                text = _ocr_page(page)
                if text.strip():
                    ocr_pages += 1
            pages.append(PageText(page_number=i, text=text))

    doc = ExtractedDocument(source_path=path, pages=pages)

    if not doc.full_text.strip():
        hint = ("Install the Tesseract binary + `pytesseract` to enable OCR."
                if not use_ocr else "OCR ran but produced no text.")
        raise ValueError(
            f"No extractable text in {path} -- likely a scanned/image PDF. {hint}"
        )
    return doc


def _ocr_available() -> bool:
    try:
        import pytesseract  # noqa: F401
        return True
    except Exception:
        return False


def _ocr_page(page) -> str:
    """OCR a single pdfplumber page via Tesseract. Returns '' if OCR isn't
    available or fails, so ingestion degrades gracefully."""
    try:
        import pytesseract

        cmd = os.environ.get("TESSERACT_CMD")
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
        image = page.to_image(resolution=300).original  # PIL.Image
        return pytesseract.image_to_string(image) or ""
    except Exception as e:
        print(f"[pdf_extract] OCR failed on page {getattr(page, 'page_number', '?')}: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """Sliding-window chunker (fallback for unstructured text or long sections)."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


# Heading patterns common in industrial reports/manuals: "1. Summary",
# "2.3 Findings", "SECTION 4", "APPENDIX A", or a short Title-Case/UPPER line.
_HEADING = re.compile(
    r"^\s*(?:"
    r"(?:\d+(?:\.\d+)*\.?\s+[A-Z][^\n]{0,60})"        # 1. / 2.3 Findings
    r"|(?:SECTION\s+\d+[^\n]*)"                        # SECTION 4 ...
    r"|(?:APPENDIX\s+[A-Z][^\n]*)"                     # APPENDIX A
    r"|(?:[A-Z][A-Z0-9 /&\-]{3,50})"                   # ALL-CAPS heading line
    r")\s*$",
    re.MULTILINE,
)


def chunk_structured(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[dict]:
    """Structure-aware chunker: split on section headings so each chunk is a
    coherent section (with its heading as a label), and sliding-window only the
    sections that are longer than `chunk_size`. Returns [{text, section}].

    This makes citations point at a real section ("Findings") and keeps related
    facts together, improving both retrieval and answer quality vs. a blind
    fixed-size window. Falls back to plain windowing if no headings are found."""
    matches = list(_HEADING.finditer(text))
    if not matches:
        return [{"text": c, "section": None} for c in chunk_text(text, chunk_size, overlap)]

    # Preamble before the first heading.
    segments: list[tuple[str | None, str]] = []
    if matches[0].start() > 0:
        pre = text[: matches[0].start()].strip()
        if pre:
            segments.append((None, pre))
    for i, m in enumerate(matches):
        heading = m.group(0).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        segments.append((heading, (heading + "\n" + body).strip()))

    out: list[dict] = []
    for heading, seg in segments:
        if len(seg) <= chunk_size:
            out.append({"text": seg, "section": heading})
        else:
            for c in chunk_text(seg, chunk_size, overlap):
                out.append({"text": c, "section": heading})
    return out
