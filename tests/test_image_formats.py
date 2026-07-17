"""HEIC/AVIF вход-выход и EXIF-автоповорот на реальных файлах."""
from pathlib import Path

from PIL import Image

from flagship_converter.core.converters.image import ImageConverter


def _convert(src: Path, dst: Path, quality: int = 85) -> None:
    ImageConverter().convert(src, dst, {"quality": quality}, lambda: False, None)


def _make_heic(path: Path) -> None:
    img = Image.new("RGB", (32, 16), "red")
    img.save(path, format="HEIF")


def test_heic_input_supported():
    conv = ImageConverter()
    assert {".heic", ".heif", ".avif"} <= conv.supported_inputs
    assert "avif" in conv.supported_outputs


def test_heic_to_jpg(tmp_path):
    src = tmp_path / "photo.heic"
    _make_heic(src)
    dst = tmp_path / "photo.jpg"
    _convert(src, dst)
    with Image.open(dst) as out:
        assert out.format == "JPEG"
        assert out.size == (32, 16)


def test_avif_to_png(tmp_path):
    src = tmp_path / "pic.avif"
    Image.new("RGB", (20, 10), "blue").save(src, format="AVIF")
    dst = tmp_path / "pic.png"
    _convert(src, dst)
    with Image.open(dst) as out:
        assert out.format == "PNG"
        assert out.size == (20, 10)


def test_png_to_avif_with_quality(tmp_path):
    src = tmp_path / "pic.png"
    Image.new("RGBA", (20, 20), (255, 0, 0, 128)).save(src, format="PNG")
    dst = tmp_path / "pic.avif"
    _convert(src, dst, quality=70)
    with Image.open(dst) as out:
        assert out.format == "AVIF"


def test_exif_orientation_applied(tmp_path):
    src = tmp_path / "rot.jpg"
    img = Image.new("RGB", (40, 20), "green")
    exif = img.getexif()
    exif[0x0112] = 6  # поворот на 90° по часовой
    img.save(src, format="JPEG", exif=exif)
    dst = tmp_path / "rot.png"
    _convert(src, dst)
    with Image.open(dst) as out:
        assert out.size == (20, 40)
