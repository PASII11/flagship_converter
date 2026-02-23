"""Общие утилиты для работы с медиа и внешними бинарниками."""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

# Регулярки для парсинга вывода FFmpeg
DURATION_RE = re.compile(r"Duration:\s*(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+\.\d+)")
TIME_RE = re.compile(r"time=(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+\.\d+)")


def _time_to_seconds(hours: str, minutes: str, seconds: str) -> float:
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def get_binary_path(name: str, win_default_paths: list[str] | None = None) -> str:
    """Ищет бинарник в бандле PyInstaller, затем в PATH, затем по дефолтным путям Windows."""
    exe_name = f"{name}.exe" if sys.platform == "win32" else name

    # 1. Ищем в бандле (когда скомпилировано через PyInstaller)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundle_path = Path(sys._MEIPASS) / exe_name
        if bundle_path.exists():
            return str(bundle_path)

    # 2. Ищем по дефолтным путям (только Windows)
    if sys.platform == "win32" and win_default_paths:
        for p in win_default_paths:
            full_path = Path(p) / exe_name
            if full_path.exists():
                return str(full_path)

    # 3. Возвращаем имя (надеемся, что оно есть в PATH)
    return name


def get_ffmpeg_path() -> str:
    return get_binary_path("ffmpeg")


def get_wkhtmltopdf_path() -> str:
    return get_binary_path(
        "wkhtmltopdf",
        win_default_paths=[r"C:\Program Files\wkhtmltopdf\bin", r"C:\Program Files (x86)\wkhtmltopdf\bin"]
    )


def run_ffmpeg(
    cmd: list[str],
    cancel_cb: Callable[[], bool],
    progress_cb: Callable[[int], None] | None = None,
) -> None:
    """Запустить FFmpeg в фоне с парсингом прогресса."""
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
    )

    error_log: list[str] = []
    total_seconds = 0.0

    while True:
        if cancel_cb():
            process.terminate()
            process.wait()
            return

        if process.stderr:
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break
            if not line:
                continue

            error_log.append(line.strip())
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
    if process.returncode != 0 and not cancel_cb():
        err_str = "\n".join(error_log)
        raise RuntimeError(f"FFmpeg error (code {process.returncode}):\n{err_str}")
