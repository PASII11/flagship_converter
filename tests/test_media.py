"""Хелпер аргументов аудио-кодирования."""
import pytest

from flagship_converter.core.converters.media import audio_encode_args


def test_flac_uses_flac_codec():
    assert audio_encode_args("flac", "192k") == ["-c:a", "flac"]


def test_wav_uses_pcm():
    assert audio_encode_args("wav", "192k") == ["-c:a", "pcm_s16le"]


def test_lossy_formats_use_bitrate():
    for ext in ("mp3", "aac", "ogg"):
        assert audio_encode_args(ext, "256k") == ["-b:a", "256k"]


def test_compute_size_bitrate_exact():
    from flagship_converter.core.converters.media import compute_size_bitrate

    assert compute_size_bitrate(8, 10.0, 128_000) == 6_247_342


def test_compute_size_bitrate_too_small():
    from flagship_converter.core.converters.media import compute_size_bitrate

    with pytest.raises(RuntimeError):
        compute_size_bitrate(8, 36000.0, 128_000)


def test_compute_size_bitrate_zero_duration():
    from flagship_converter.core.converters.media import compute_size_bitrate

    with pytest.raises(RuntimeError):
        compute_size_bitrate(8, 0.0, 128_000)


SAMPLE_FFMPEG_STDERR = (
    "Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'in.mp4':\n"
    "  Duration: 00:01:30.50, start: 0.000000, bitrate: 1064 kb/s\n"
)


def test_probe_duration_parses_stderr(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from flagship_converter.core.converters import media as media_mod

    monkeypatch.setattr(media_mod, "get_ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(
        media_mod.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(stderr=SAMPLE_FFMPEG_STDERR),
    )
    assert media_mod.probe_duration_seconds(tmp_path / "in.mp4") == 90.5


def test_probe_duration_garbage_raises(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from flagship_converter.core.converters import media as media_mod

    monkeypatch.setattr(media_mod, "get_ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(
        media_mod.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(stderr="no duration here"),
    )
    with pytest.raises(RuntimeError):
        media_mod.probe_duration_seconds(tmp_path / "in.mp4")
