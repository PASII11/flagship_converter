"""Тесты PDF → DOCX конвертации с сохранением оформления."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image


def _make_digital_pdf(
    path: Path,
    paragraphs: list[str] | None = None,
    with_image: bool = False,
) -> None:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    y = 72.0
    lines = paragraphs or ["Hello PDF world, this is a digital document for testing."]
    for text in lines:
        page.insert_text((72, y), text, fontsize=12)
        y += 20
    if with_image:
        image = Image.new("RGB", (120, 60), (30, 120, 220))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        page.insert_image(fitz.Rect(72, y, 192, y + 60), stream=buffer.getvalue())
    doc.save(str(path))
    doc.close()


def _make_image_only_pdf(path: Path) -> None:
    import fitz

    image = Image.new("RGB", (200, 100), (200, 30, 30))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    doc = fitz.open()
    page = doc.new_page(width=300, height=200)
    page.insert_image(fitz.Rect(50, 50, 250, 150), stream=buffer.getvalue())
    doc.save(str(path))
    doc.close()


def test_sanitize_for_xml_strips_control_chars() -> None:
    from flagship_converter.core.converters.pdf_docx import sanitize_for_xml

    assert sanitize_for_xml("ok\x00\x0btext") == "oktext"


def test_pdf_has_text_layer_true_for_digital(tmp_path: Path) -> None:
    from flagship_converter.core.converters.pdf_docx import pdf_has_text_layer

    pdf = tmp_path / "digital.pdf"
    _make_digital_pdf(pdf)

    assert pdf_has_text_layer(pdf) is True


def test_pdf_has_text_layer_false_for_image_only(tmp_path: Path) -> None:
    from flagship_converter.core.converters.pdf_docx import pdf_has_text_layer

    pdf = tmp_path / "scan.pdf"
    _make_image_only_pdf(pdf)

    assert pdf_has_text_layer(pdf) is False
