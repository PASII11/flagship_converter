"""Видео → аудио и видео → GIF: команды FFmpeg, прогресс, отмена."""
from pathlib import Path

import pytest

from flagship_converter.core.converters import video as video_mod
from flagship_converter.core.converters.video import AUDIO_TARGETS, VideoConverter


@pytest.fixture()
def ffmpeg_calls(monkeypatch):
    """Мок run_ffmpeg: собирает команды, зовёт progress_cb(100)."""
    calls: list[list[str]] = []

    def fake_run(cmd, cancel_cb, progress_cb=None):
        calls.append(list(cmd))
        if progress_cb:
            progress_cb(100)

    monkeypatch.setattr(video_mod, "run_ffmpeg", fake_run)
    monkeypatch.setattr(video_mod, "get_ffmpeg_path", lambda: "ffmpeg")
    return calls


def _convert(tmp_path: Path, target: str, params: dict | None = None):
    conv = VideoConverter()
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    out = tmp_path / f"out.{target}"
    conv.convert(src, out, params or {}, lambda: False, None)
    return out


def test_audio_targets_in_supported_outputs():
    assert AUDIO_TARGETS <= VideoConverter.supported_outputs


def test_mp3_extraction_strips_video(ffmpeg_calls, tmp_path):
    _convert(tmp_path, "mp3", {"audio_bitrate": "256k"})
    (cmd,) = ffmpeg_calls
    assert "-vn" in cmd
    assert cmd[cmd.index("-b:a") + 1] == "256k"
    assert "-c:v" not in cmd


def test_wav_extraction_uses_pcm(ffmpeg_calls, tmp_path):
    _convert(tmp_path, "wav")
    (cmd,) = ffmpeg_calls
    assert "-vn" in cmd
    assert cmd[cmd.index("-c:a") + 1] == "pcm_s16le"


def test_flac_extraction_uses_flac(ffmpeg_calls, tmp_path):
    _convert(tmp_path, "flac")
    (cmd,) = ffmpeg_calls
    assert cmd[cmd.index("-c:a") + 1] == "flac"


def test_video_target_still_uses_video_codec(ffmpeg_calls, tmp_path):
    _convert(tmp_path, "mp4")
    (cmd,) = ffmpeg_calls
    assert "-c:v" in cmd
    assert "-vn" not in cmd


def test_gif_two_pass_palette(ffmpeg_calls, tmp_path):
    _convert(tmp_path, "gif", {"gif_fps": 20, "gif_width": 320})
    assert len(ffmpeg_calls) == 2
    pass1, pass2 = ffmpeg_calls
    vf = pass1[pass1.index("-vf") + 1]
    assert vf == "fps=20,scale=320:-1:flags=lanczos,palettegen"
    lavfi = pass2[pass2.index("-lavfi") + 1]
    assert lavfi == "fps=20,scale=320:-1:flags=lanczos[x];[x][1:v]paletteuse"
    second_input = pass2[pass2.index("-i", pass2.index("-i") + 1) + 1]
    assert second_input.endswith(".palette.png")


def test_gif_original_width_skips_scale(ffmpeg_calls, tmp_path):
    _convert(tmp_path, "gif", {"gif_width": 0})
    pass1, _pass2 = ffmpeg_calls
    vf = pass1[pass1.index("-vf") + 1]
    assert vf == "fps=15,palettegen"


def test_gif_progress_maps_to_halves(ffmpeg_calls, tmp_path):
    seen: list[int] = []
    conv = VideoConverter()
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    conv.convert(src, tmp_path / "out.gif", {}, lambda: False, seen.append)
    assert seen == [50, 100]


def test_gif_cancel_between_passes(tmp_path, monkeypatch):
    calls: list[list[str]] = []
    cancelled = {"flag": False}

    def fake_run(cmd, cancel_cb, progress_cb=None):
        calls.append(list(cmd))
        cancelled["flag"] = True

    monkeypatch.setattr(video_mod, "run_ffmpeg", fake_run)
    monkeypatch.setattr(video_mod, "get_ffmpeg_path", lambda: "ffmpeg")
    conv = VideoConverter()
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    conv.convert(src, tmp_path / "out.gif", {}, lambda: cancelled["flag"], None)
    assert len(calls) == 1


def test_gif_palette_removed_on_error(tmp_path, monkeypatch):
    def fake_run(cmd, cancel_cb, progress_cb=None):
        if "-vf" in cmd:
            Path(cmd[-1]).write_bytes(b"palette")
            return
        raise RuntimeError("pass 2 failed")

    monkeypatch.setattr(video_mod, "run_ffmpeg", fake_run)
    monkeypatch.setattr(video_mod, "get_ffmpeg_path", lambda: "ffmpeg")
    conv = VideoConverter()
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    out = tmp_path / "out.gif"
    with pytest.raises(RuntimeError):
        conv.convert(src, out, {}, lambda: False, None)
    assert not out.with_suffix(".palette.png").exists()


@pytest.fixture()
def fixed_duration(monkeypatch):
    monkeypatch.setattr(video_mod, "probe_duration_seconds", lambda _p: 10.0)


def test_target_size_computes_bitrate(ffmpeg_calls, fixed_duration, tmp_path):
    _convert(tmp_path, "mp4", {"target_size_mb": 8})
    (cmd,) = ffmpeg_calls
    assert cmd[cmd.index("-b:v") + 1] == "6247342"
    assert cmd[cmd.index("-maxrate") + 1] == "6247342"
    assert cmd[cmd.index("-bufsize") + 1] == "12494684"
    assert cmd[cmd.index("-b:a") + 1] == "128k"


def test_target_size_webm_uses_opus_128k(ffmpeg_calls, fixed_duration, tmp_path):
    _convert(tmp_path, "webm", {"target_size_mb": 8})
    (cmd,) = ffmpeg_calls
    assert cmd[cmd.index("-c:a") + 1] == "libopus"
    assert cmd[cmd.index("-b:a") + 1] == "128k"
    assert "-maxrate" in cmd


def test_target_size_too_small_raises(ffmpeg_calls, tmp_path, monkeypatch):
    monkeypatch.setattr(video_mod, "probe_duration_seconds", lambda _p: 36000.0)
    with pytest.raises(RuntimeError):
        _convert(tmp_path, "mp4", {"target_size_mb": 8})
    assert ffmpeg_calls == []


def test_no_target_size_keeps_manual_bitrate(ffmpeg_calls, tmp_path):
    _convert(tmp_path, "mp4", {"video_bitrate": "5M"})
    (cmd,) = ffmpeg_calls
    assert cmd[cmd.index("-b:v") + 1] == "5M"
    assert "-maxrate" not in cmd
    assert cmd[cmd.index("-b:a") + 1] == "192k"


def test_video_output_forces_8bit_pixel_format(ffmpeg_calls, tmp_path):
    _convert(tmp_path, "mp4", {"video_codec": "amd"})
    (cmd,) = ffmpeg_calls
    assert cmd[cmd.index("-c:v") + 1] == "h264_amf"
    assert cmd[cmd.index("-pix_fmt") + 1] == "yuv420p"


def test_webm_output_forces_8bit_pixel_format(ffmpeg_calls, tmp_path):
    _convert(tmp_path, "webm", {})
    (cmd,) = ffmpeg_calls
    assert cmd[cmd.index("-pix_fmt") + 1] == "yuv420p"
