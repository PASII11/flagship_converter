"""Движок конвертации: сборка плана и выполнение задач с умной многопоточностью."""
from __future__ import annotations

import concurrent.futures
import os
from collections import defaultdict
from collections.abc import Callable, Iterable
from pathlib import Path

from flagship_converter.core.converters.audio import AudioConverter
from flagship_converter.core.converters.document import DocConverter
from flagship_converter.core.converters.image import ImageConverter
from flagship_converter.core.converters.video import VideoConverter
from flagship_converter.core.models import ConversionJob, ConversionPlan, JobStatus


class ConversionEngine:
    def __init__(self) -> None:
        self._converters = [
            ImageConverter(),
            AudioConverter(),
            VideoConverter(),
            DocConverter(),
        ]

    def collect_files(self, paths: Iterable[str | Path]) -> list[Path]:
        result: list[Path] = []
        for raw in paths:
            try:
                p = Path(raw)
                if p.exists() and p.is_file():
                    result.append(p)
            except OSError:
                pass
        return result

    def build_job(
        self,
        file_path: Path,
        output_dir: Path,
        target_ext: str,
        overwrite: bool,
        params: dict[str, object],
    ) -> ConversionJob | None:
        """Построить задачу для одного файла. Возвращает None если формат не поддерживается."""
        for converter in self._converters:
            if converter.can_handle(file_path):
                output_path = converter.build_output_path(
                    file_path, output_dir, target_ext, overwrite
                )
                return ConversionJob(
                    input_path=file_path,
                    output_path=output_path,
                    converter=type(converter).__name__,
                    params=params,
                    target_ext=target_ext,
                )
        return None

    def build_plan(
        self,
        paths: Iterable[str | Path],
        output_dir: Path,
        target_ext: str,
        overwrite: bool,
        quality: int,
        lossless_webp: bool,
        audio_bitrate: str,
        video_bitrate: str,
        video_codec: str,
    ) -> ConversionPlan:
        plan = ConversionPlan()
        files = self.collect_files(paths)
        params: dict[str, object] = {
            "quality": quality,
            "lossless_webp": lossless_webp,
            "audio_bitrate": audio_bitrate,
            "video_bitrate": video_bitrate,
            "video_codec": video_codec,
        }
        for file_path in files:
            job = self.build_job(file_path, output_dir, target_ext, overwrite, params)
            if job:
                plan.jobs.append(job)
        return plan

    def execute_plan(
        self,
        plan: ConversionPlan,
        cancel_cb: Callable[[], bool],
        on_job_started: Callable[[str], None],
        on_job_finished: Callable[[str], None],
        on_job_failed: Callable[[str, str], None],
        on_job_progress: Callable[[str, int], None] | None = None,
    ) -> None:
        converter_map = {type(c).__name__: c for c in self._converters}

        # Шаг 1. Группируем задачи по типам конвертеров (для разного уровня параллелизма)
        jobs_by_converter: dict[str, list[ConversionJob]] = defaultdict(list)
        for job in plan.jobs:
            if cancel_cb():
                job.status = JobStatus.CANCELLED
                continue
            jobs_by_converter[job.converter].append(job)

        # Функция, которая будет крутиться в отдельном потоке
        def _process_job(job: ConversionJob, converter: object) -> None:
            if cancel_cb():
                job.status = JobStatus.CANCELLED
                return

            job.status = JobStatus.RUNNING
            on_job_started(job.id)

            def progress_hook(percent: int) -> None:
                if on_job_progress:
                    on_job_progress(job.id, percent)

            try:
                converter.convert(  # type: ignore[attr-defined]
                    job.input_path,
                    job.output_path,
                    job.params,
                    cancel_cb,
                    progress_hook
                )
                job.status = JobStatus.DONE
                on_job_finished(job.id)
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
                on_job_failed(job.id, job.error)

        # Получаем количество ядер, чтобы масштабировать обработку изображений
        cpu_cores = os.cpu_count() or 4

        # Шаг 2. Выполняем каждую группу с её собственным лимитом потоков
        for conv_name, jobs in jobs_by_converter.items():
            if cancel_cb():
                break

            converter = converter_map.get(conv_name)
            if not converter:
                for j in jobs:
                    j.status = JobStatus.FAILED
                    j.error = f"Конвертер '{conv_name}' не найден"
                    on_job_failed(j.id, j.error)
                continue

            # Балансировка нагрузки: определяем сколько задач можно запустить одновременно
            if conv_name == "ImageConverter":
                workers = cpu_cores  # Картинки отлично параллелятся, загружаем все ядра
            elif conv_name == "AudioConverter":
                workers = min(4, cpu_cores)  # Аудио упирается в скорость диска
            elif conv_name == "VideoConverter":
                workers = 2  # Видео требует много ресурсов, сам FFmpeg внутри многопоточный
            else:
                workers = 1  # DocConverter: строго 1 поток во избежание OOM и багов PyInstaller

            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(_process_job, job, converter) for job in jobs]

                # Ждем завершения этого батча, прежде чем переходить к следующему типу файлов
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()
                    except Exception:
                        # Исключения уже перехвачены внутри _process_job, так что просто идем дальше
                        pass
