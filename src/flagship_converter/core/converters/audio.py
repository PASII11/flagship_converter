"""Конвертер аудио на базе FFmpeg."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from flagship_converter.core.converters.base import safe_output_path
from flagship_converter.core.converters.media import audio_encode_args, get_ffmpeg_path, run_ffmpeg

SUPPORTED_INPUT = {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma"}
SUPPORTED_OUTPUT = {"mp3", "wav", "flac", "aac", "ogg"}


class AudioConverter:
    supported_inputs = SUPPORTED_INPUT
    supported_outputs = SUPPORTED_OUTPUT

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in SUPPORTED_INPUT

    def build_output_path(
        self,
        input_path: Path,
        output_dir: Path,
        target_ext: str,
        overwrite: bool,
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        base = output_dir / f"{input_path.stem}.{target_ext.lstrip('.')}"
        return safe_output_path(base, overwrite)

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        params: dict[str, object],
        cancel_cb: Callable[[], bool],
        progress_cb: Callable[[int], None] | None = None,
    ) -> None:
        if cancel_cb():
            return

        target_ext = output_path.suffix.lower().lstrip(".")
        audio_bitrate = str(params.get("audio_bitrate", "192k"))

        cmd = [get_ffmpeg_path(), "-y", "-i", str(input_path)]
        cmd.extend(audio_encode_args(target_ext, audio_bitrate))
        cmd.append(str(output_path))
        run_ffmpeg(cmd, cancel_cb, progress_cb)
