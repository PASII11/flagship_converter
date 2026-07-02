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

    # 2. Ищем в локальной папке сборочных бинарников при запуске из исходников.
    local_tool = Path.cwd() / "build_tools" / exe_name
    if local_tool.exists():
        return str(local_tool)

    try:
        repo_tool = Path(__file__).resolve().parents[4] / "build_tools" / exe_name
        if repo_tool.exists():
            return str(repo_tool)
    except IndexError:
        pass

    # 3. Ищем по дефолтным путям (только Windows)
    if sys.platform == "win32" and win_default_paths:
        for p in win_default_paths:
            full_path = Path(p) / exe_name
            if full_path.exists():
                return str(full_path)

    # 4. Ищем в PATH и явно сообщаем, если бинарника нет.
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
    # Используем iter для чтения до EOF (пустой строки)
    for line in iter(out_stream.readline, ""):  # type: ignore[attr-defined]
        if line:
            q.put(line)
    out_stream.close()  # type: ignore[attr-defined]


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
        bufsize=1,  # Построчная буферизация
    )

    if not process.stderr:
        _terminate_process(process)
        raise RuntimeError("Не удалось открыть stderr процесса FFmpeg")

    # Создаем очередь и запускаем поток-читатель
    q: queue.Queue[str] = queue.Queue()
    t = threading.Thread(target=_enqueue_output, args=(process.stderr, q), daemon=True)
    t.start()

    error_log: list[str] = []
    total_seconds = 0.0

    while True:
        # 1. Проверяем флаг отмены из UI
        if cancel_cb():
            _terminate_process(process)
            t.join(timeout=1.0)
            raise ConversionCancelled()

        # 2. Неблокирующее чтение из очереди
        try:
            line = q.get(timeout=0.1)
        except queue.Empty:
            # Очередь пуста. Если процесс завершен — выходим из цикла
            if process.poll() is not None:
                break
            continue

        line = line.strip()
        if not line:
            continue

        error_log.append(line)
        if len(error_log) > 20:
            error_log.pop(0)

        # 3. Парсинг прогресса
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
    t.join(timeout=1.0)  # Даем потоку секунду на корректное завершение

    if process.returncode != 0 and not cancel_cb():
        err_str = "\n".join(error_log)
        raise RuntimeError(f"FFmpeg error (code {process.returncode}):\n{err_str}")
