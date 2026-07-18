"""Общие утилиты для работы с медиа и внешними бинарниками."""
from __future__ import annotations

import queue
import re
import shutil
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path

from flagship_converter.core.converters.base import ConversionCancelled
from flagship_converter.i18n import t

DURATION_RE = re.compile(r"Duration:\s*(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+\.\d+)")
TIME_RE = re.compile(r"time=(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+\.\d+)")


def _time_to_seconds(hours: str, minutes: str, seconds: str) -> float:
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def get_binary_path(name: str, win_default_paths: list[str] | None = None) -> str:
    """Ищет бинарник в бандле PyInstaller, затем в PATH, затем по дефолтным путям Windows."""
    exe_name = f"{name}.exe" if sys.platform == "win32" else name

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundle_path = Path(sys._MEIPASS) / exe_name
        if bundle_path.exists():
            return str(bundle_path)

    local_tool = Path.cwd() / "build_tools" / exe_name
    if local_tool.exists():
        return str(local_tool)

    try:
        repo_tool = Path(__file__).resolve().parents[4] / "build_tools" / exe_name
        if repo_tool.exists():
            return str(repo_tool)
    except IndexError:
        pass

    if sys.platform == "win32" and win_default_paths:
        for p in win_default_paths:
            full_path = Path(p) / exe_name
            if full_path.exists():
                return str(full_path)

    found = shutil.which(exe_name) or shutil.which(name)
    if found:
        return found

    raise RuntimeError(
        f"Required binary '{exe_name}' was not found in the app bundle, default paths, or PATH."
    )


def get_ffmpeg_path() -> str:
    return get_binary_path("ffmpeg")


def get_wkhtmltopdf_path() -> str:
    return get_binary_path(
        "wkhtmltopdf",
        win_default_paths=[
            r"C:\Program Files\wkhtmltopdf\bin",
            r"C:\Program Files (x86)\wkhtmltopdf\bin",
        ],
    )


def _enqueue_output(out_stream: object, q: queue.Queue[str]) -> None:
    """Фоновый поток для непрерывного чтения вывода процесса без блокировки."""
    for line in iter(out_stream.readline, ""):
        if line:
            q.put(line)
    out_stream.close()


def _terminate_process(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def run_ffmpeg(
    cmd: list[str],
    cancel_cb: Callable[[], bool],
    progress_cb: Callable[[int], None] | None = None,
) -> None:
    """Запустить FFmpeg в фоне с потокобезопасным чтением прогресса."""
    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=creationflags,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    if not process.stderr:
        _terminate_process(process)
        raise RuntimeError(t("Не удалось открыть stderr процесса FFmpeg"))

    q: queue.Queue[str] = queue.Queue()
    output_thread = threading.Thread(target=_enqueue_output, args=(process.stderr, q), daemon=True)
    output_thread.start()

    error_log: list[str] = []
    total_seconds = 0.0

    while True:
        if cancel_cb():
            _terminate_process(process)
            output_thread.join(timeout=1.0)
            raise ConversionCancelled()

        try:
            line = q.get(timeout=0.1)
        except queue.Empty:
            if process.poll() is not None:
                break
            continue

        line = line.strip()
        if not line:
            continue

        error_log.append(line)
        if len(error_log) > 20:
            error_log.pop(0)

        if progress_cb:
            if total_seconds == 0.0:
                dur_match = DURATION_RE.search(line)
                if dur_match:
                    total_seconds = _time_to_seconds(
                        dur_match.group("hours"),
                        dur_match.group("minutes"),
                        dur_match.group("seconds"),
                    )
            else:
                time_match = TIME_RE.search(line)
                if time_match:
                    current_sec = _time_to_seconds(
                        time_match.group("hours"),
                        time_match.group("minutes"),
                        time_match.group("seconds"),
                    )
                    percent = min(int((current_sec / total_seconds) * 100), 100)
                    progress_cb(percent)

    process.wait()
    output_thread.join(timeout=1.0)

    if process.returncode != 0 and not cancel_cb():
        err_str = "\n".join(error_log)
        raise RuntimeError(f"FFmpeg error (code {process.returncode}):\n{err_str}")


def audio_encode_args(target_ext: str, audio_bitrate: str) -> list[str]:
    """Аргументы FFmpeg для кодирования аудио: одинаковы для аудио- и видео-входов."""
    if target_ext == "flac":
        return ["-c:a", "flac"]
    if target_ext == "wav":
        return ["-c:a", "pcm_s16le"]
    return ["-b:a", audio_bitrate]


SIZE_BITRATE_FLOOR_BPS = 100_000
SIZE_CONTAINER_MARGIN = 0.95


def probe_duration_seconds(input_path: Path) -> float:
    """Длительность видео из заголовка: ffmpeg -i пишет Duration в stderr."""
    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    result = subprocess.run(
        [get_ffmpeg_path(), "-i", str(input_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    match = DURATION_RE.search(result.stderr or "")
    if not match:
        raise RuntimeError(t("Не удалось определить длительность видео"))
    return _time_to_seconds(match["hours"], match["minutes"], match["seconds"])


def compute_size_bitrate(target_mb: int, duration_s: float, audio_bps: int) -> int:
    """Видео-битрейт для попадания в целевой размер; 5% запас на контейнер."""
    if duration_s <= 0:
        raise RuntimeError(t("Не удалось определить длительность видео"))
    budget_bits = target_mb * 8 * 1024 * 1024 * SIZE_CONTAINER_MARGIN
    video_bps = int(budget_bits / duration_s) - audio_bps
    if video_bps < SIZE_BITRATE_FLOOR_BPS:
        raise RuntimeError(t("Целевой размер слишком мал для этой длительности"))
    return video_bps
