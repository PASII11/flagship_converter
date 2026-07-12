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
