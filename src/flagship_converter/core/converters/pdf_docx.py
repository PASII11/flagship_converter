"""PDF → DOCX конвертация с сохранением оформления (pdf2docx + Docling)."""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_XML_INCOMPATIBLE = re.compile(
    "[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\x7f"
    "\\ud800-\\udfff\\ufdd0-\\ufddf\\ufffe\\uffff]"
)


def sanitize_for_xml(text: str) -> str:
    return _XML_INCOMPATIBLE.sub("", text)


def pdf_has_text_layer(
    input_path: Path,
    min_chars_per_page: int = 25,
    min_text_page_ratio: float = 0.5,
) -> bool:
    """Цифровой PDF: не меньше половины страниц дают > 25 извлекаемых символов."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(input_path))
    try:
        page_count = len(pdf)
        if page_count == 0:
            return False
        text_pages = 0
        for index in range(page_count):
            page = pdf[index]
            try:
                textpage = page.get_textpage()
                try:
                    text = textpage.get_text_range().strip()
                finally:
                    textpage.close()
            finally:
                page.close()
            if len(text) > min_chars_per_page:
                text_pages += 1
        return text_pages / page_count >= min_text_page_ratio
    finally:
        pdf.close()


def convert_with_pdf2docx(input_path: Path, output_path: Path) -> None:
    """Цифровой путь: pdf2docx воспроизводит раскладку, шрифты, картинки, таблицы."""
    from pdf2docx import Converter

    logging.getLogger("pdf2docx").setLevel(logging.ERROR)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    converter = Converter(str(input_path))
    try:
        converter.convert(str(output_path))
    finally:
        converter.close()

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("pdf2docx did not produce a DOCX output.")
