from __future__ import annotations

import io
from typing import Optional

from PIL import Image
from pypdf import PdfReader
import pytesseract

from app.core.config import settings


def _configure_ocr_tools() -> None:
    """
    Configure external OCR dependencies (Windows-friendly).

    pytesseract needs the `tesseract` binary. If it's not on PATH, users can set:
      - TESSERACT_CMD="C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    """
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


def extract_text_from_pdf(data: bytes) -> str:
    """
    Attempts to extract text from a PDF.
    If the PDF is scanned, this may return an empty string unless OCR fallback is enabled.
    """
    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            parts.append(page_text)
    return "\n\n".join(parts).strip()


def extract_text_from_image(data: bytes) -> str:
    _configure_ocr_tools()
    image = Image.open(io.BytesIO(data)).convert("RGB")
    text = pytesseract.image_to_string(image)
    return (text or "").strip()


def try_pdf_ocr_fallback(data: bytes) -> Optional[str]:
    """
    Optional OCR fallback for scanned PDFs using pdf2image + pytesseract.
    Requires poppler installed and available in PATH on Windows.
    Returns None if dependencies/runtime are not available.
    """
    try:
        from pdf2image import convert_from_bytes
    except Exception:
        return None

    try:
        _configure_ocr_tools()
        images = convert_from_bytes(data, poppler_path=settings.poppler_path or None)
        parts: list[str] = []
        for img in images:
            parts.append((pytesseract.image_to_string(img) or "").strip())
        out = "\n\n".join([p for p in parts if p]).strip()
        return out or None
    except Exception:
        return None

