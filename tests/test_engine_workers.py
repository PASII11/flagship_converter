"""Ограничение параллелизма движка."""
from flagship_converter.core.engine import ConversionEngine


def test_default_unlimited():
    engine = ConversionEngine()
    assert engine._effective_workers(8) == 8


def test_cap_applies():
    engine = ConversionEngine(max_workers=2)
    assert engine._effective_workers(8) == 2
    assert engine._effective_workers(1) == 1


def test_zero_or_negative_means_auto():
    assert ConversionEngine(max_workers=0)._effective_workers(6) == 6


def test_supported_input_extensions_union():
    exts = ConversionEngine().supported_input_extensions()
    assert {".jpg", ".mp3", ".mp4", ".pdf"} <= exts


def test_collect_files_expands_folders(tmp_path):
    (tmp_path / "sub").mkdir()
    keep = tmp_path / "sub" / "a.jpg"
    keep.write_bytes(b"x")
    (tmp_path / "sub" / "skip.xyz").write_bytes(b"x")
    assert ConversionEngine().collect_files([tmp_path]) == [keep]
