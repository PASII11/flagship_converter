"""Конвертер видео на базе FFmpeg."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from flagship_converter.core.converters.base import safe_output_path
from flagship_converter.core.converters.media import get_ffmpeg_path, run_ffmpeg

SUPPORTED_INPUT = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".m4v"}
SUPPORTED_OUTPUT = {"mp4", "mkv", "avi", "webm"}


class VideoConverter:
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
        video_bitrate = str(params.get("video_bitrate", "2.5M"))
        codec_str = str(params.get("video_codec", "CPU (x264)"))

        cmd = [get_ffmpeg_path(), "-y", "-i", str(input_path)]

        if target_ext == "webm":
            cmd.extend(["-c:v", "libvpx-vp9", "-b:v", video_bitrate, "-c:a", "libopus"])
        else:
            # Выбор аппаратного кодека
            if "AMD" in codec_str:
                vcodec = "h264_amf"
            elif "NVIDIA" in codec_str:
                vcodec = "h264_nvenc"
            elif "Intel" in codec_str:
                vcodec = "h264_qsv"
            else:
                vcodec = "libx264"

            cmd.extend(["-c:v", vcodec, "-b:v", video_bitrate, "-c:a", "aac", "-b:a", "192k"])

        cmd.append(str(output_path))
        run_ffmpeg(cmd, cancel_cb, progress_cb)
