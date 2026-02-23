"""Smoke-тесты: проверка импортов и базовой логики без GUI."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image


def test_import_package() -> None:
    import flagship_converter
    assert flagship_converter.__version__ == "0.1.0"


def test_import_app_main() -> None:
    from flagship_converter.app import main
    assert callable(main)


def test_image_converter_roundtrip() -> None:
    """Создать PNG → конвертировать в JPEG → файл существует и не пустой."""
    from flagship_converter.core.converters.image import ImageConverter

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "test.png"
        out = Path(tmp) / "out" / "test.jpg"

        img = Image.new("RGB", (64, 64), color=(120, 80, 200))
        img.save(src)

        converter = ImageConverter()
        assert converter.can_handle(src)
        out.parent.mkdir(parents=True, exist_ok=True)
        converter.convert(src, out, {"quality": 85}, cancel_cb=lambda: False)

        assert out.exists()
        assert out.stat().st_size > 0


def test_safe_output_path_no_collision() -> None:
    from flagship_converter.core.converters.base import safe_output_path

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "file.jpg"
        result = safe_output_path(p, overwrite=False)
        assert result == p  # файла нет — возвращаем как есть


def test_safe_output_path_collision() -> None:
    from flagship_converter.core.converters.base import safe_output_path

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "file.jpg"
        p.touch()  # имитируем существующий файл
        result = safe_output_path(p, overwrite=False)
        assert result.name == "file_1.jpg"
