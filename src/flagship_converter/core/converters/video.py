"""Конвертер видео на базе FFmpeg."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from flagship_converter.core.converters.base import safe_output_path
from flagship_converter.core.converters.media import (
    audio_encode_args,
    get_ffmpeg_path,
    run_ffmpeg,
)

SUPPORTED_INPUT = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".m4v"}
AUDIO_TARGETS = {"mp3", "wav", "flac", "aac", "ogg"}
SUPPORTED_OUTPUT = {"mp4", "mkv", "avi", "webm", "gif"} | AUDIO_TARGETS


class VideoConverter:
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
        if target_ext in AUDIO_TARGETS:
            self._convert_to_audio(input_path, output_path, params, cancel_cb, progress_cb)
            return

        if target_ext == "gif":
            self._convert_to_gif(input_path, output_path, params, cancel_cb, progress_cb)
            return

        video_bitrate = str(params.get("video_bitrate", "2.5M"))
        codec_id = str(params.get("video_codec", "auto"))

        cmd = [get_ffmpeg_path(), "-y", "-i", str(input_path)]

        if target_ext == "webm":
            cmd.extend(["-c:v", "libvpx-vp9", "-b:v", video_bitrate, "-c:a", "libopus"])
        else:
            if codec_id == "amd":
                vcodec = "h264_amf"
            elif codec_id == "nvidia":
                vcodec = "h264_nvenc"
            elif codec_id == "intel":
                vcodec = "h264_qsv"
            else:
                vcodec = "libx264"

            cmd.extend(["-c:v", vcodec, "-b:v", video_bitrate, "-c:a", "aac", "-b:a", "192k"])

        cmd.append(str(output_path))
        run_ffmpeg(cmd, cancel_cb, progress_cb)

    def _convert_to_audio(
        self,
        input_path: Path,
        output_path: Path,
        params: dict[str, object],
        cancel_cb: Callable[[], bool],
        progress_cb: Callable[[int], None] | None,
    ) -> None:
        """Извлечение аудио дорожки из видео файла."""
        target_ext = output_path.suffix.lower().lstrip(".")
        audio_bitrate = str(params.get("audio_bitrate", "192k"))
        cmd = [
            get_ffmpeg_path(), "-y", "-i", str(input_path), "-vn",
            *audio_encode_args(target_ext, audio_bitrate),
            str(output_path),
        ]
        run_ffmpeg(cmd, cancel_cb, progress_cb)

    def _convert_to_gif(
        self,
        input_path: Path,
        output_path: Path,
        params: dict[str, object],
        cancel_cb: Callable[[], bool],
        progress_cb: Callable[[int], None] | None,
    ) -> None:
        """Конвертация видео в анимированный GIF с палеттой."""
        fps = int(params.get("gif_fps", 15))
        width = int(params.get("gif_width", 480))
        filters = [f"fps={fps}"]
        if width > 0:
            filters.append(f"scale={width}:-1:flags=lanczos")
        chain = ",".join(filters)

        def first_half(percent: int) -> None:
            if progress_cb:
                progress_cb(percent // 2)

        def second_half(percent: int) -> None:
            if progress_cb:
                progress_cb(50 + percent // 2)

        palette_path = output_path.with_suffix(".palette.png")
        try:
            cmd1 = [
                get_ffmpeg_path(), "-y", "-i", str(input_path),
                "-vf", f"{chain},palettegen", str(palette_path),
            ]
            run_ffmpeg(cmd1, cancel_cb, first_half)
            if cancel_cb():
                return
            cmd2 = [
                get_ffmpeg_path(), "-y", "-i", str(input_path),
                "-i", str(palette_path),
                "-lavfi", f"{chain}[x];[x][1:v]paletteuse",
                str(output_path),
            ]
            run_ffmpeg(cmd2, cancel_cb, second_half)
        finally:
            try:
                palette_path.unlink(missing_ok=True)
            except OSError:
                pass
