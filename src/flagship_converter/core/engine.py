"""Движок конвертации: сборка плана и выполнение задач с умной многопоточностью."""
from __future__ import annotations

import concurrent.futures
import os
from collections import defaultdict
from collections.abc import Callable, Iterable
from pathlib import Path

from flagship_converter.core.converters.audio import AudioConverter
from flagship_converter.core.converters.base import ConversionCancelled, Converter
from flagship_converter.core.converters.document import DocConverter
from flagship_converter.core.converters.image import ImageConverter
from flagship_converter.core.converters.video import VideoConverter
from flagship_converter.core.models import ConversionJob, ConversionPlan, JobStatus
from flagship_converter.i18n import t


class ConversionEngine:
    def __init__(self, max_workers: int | None = None) -> None:
        self._max_workers = max_workers
        self._converters: list[Converter] = [
            ImageConverter(),
            AudioConverter(),
            VideoConverter(),
            DocConverter(),
        ]

    def set_max_workers(self, value: int | None) -> None:
        self._max_workers = value

    def _effective_workers(self, computed: int) -> int:
        if self._max_workers and self._max_workers > 0:
            return max(1, min(computed, self._max_workers))
        return computed

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
        reserved_outputs: set[Path] | None = None,
    ) -> ConversionJob | None:
        """Построить задачу для одного файла. Возвращает None если формат не поддерживается."""
        normalized_target = target_ext.lower().lstrip(".")
        for converter in self._converters:
            if converter.can_handle(file_path) and normalized_target in converter.supported_outputs:
                output_path = converter.build_output_path(
                    file_path, output_dir, normalized_target, overwrite
                )
                output_path = self._reserve_output_path(
                    output_path,
                    overwrite,
                    reserved_outputs,
                )
                return ConversionJob(
                    input_path=file_path,
                    output_path=output_path,
                    converter=type(converter).__name__,
                    params=params,
                    target_ext=normalized_target,
                    overwrite=overwrite,
                )
        return None

    def _reserve_output_path(
        self,
        output_path: Path,
        overwrite: bool,
        reserved_outputs: set[Path] | None,
    ) -> Path:
        if reserved_outputs is None:
            return output_path

        candidate = output_path
        parent = candidate.parent
        stem = candidate.stem
        suffix = candidate.suffix
        counter = 1
        while candidate in reserved_outputs or (not overwrite and candidate.exists()):
            candidate = parent / f"{stem}_{counter}{suffix}"
            counter += 1
        reserved_outputs.add(candidate)
        return candidate

    def _temp_output_path(self, output_path: Path, job_id: str) -> Path:
        return output_path.with_name(f"{output_path.stem}.{job_id}.part{output_path.suffix}")

    def _cleanup_partial(self, temp_path: Path) -> None:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass

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
        reserved_outputs: set[Path] = set()
        params: dict[str, object] = {
            "quality": quality,
            "lossless_webp": lossless_webp,
            "audio_bitrate": audio_bitrate,
            "video_bitrate": video_bitrate,
            "video_codec": video_codec,
        }
        for file_path in files:
            job = self.build_job(
                file_path,
                output_dir,
                target_ext,
                overwrite,
                params,
                reserved_outputs=reserved_outputs,
            )
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
        on_job_cancelled: Callable[[str], None] | None = None,
        on_job_progress: Callable[[str, int], None] | None = None,
    ) -> None:
        converter_map = {type(c).__name__: c for c in self._converters}

        def mark_cancelled(job: ConversionJob) -> None:
            job.status = JobStatus.CANCELLED
            if on_job_cancelled:
                on_job_cancelled(job.id)

        jobs_by_converter: dict[str, list[ConversionJob]] = defaultdict(list)
        for job in plan.jobs:
            if cancel_cb():
                mark_cancelled(job)
                continue
            jobs_by_converter[job.converter].append(job)

        def _process_job(job: ConversionJob, converter: object) -> None:
            if cancel_cb():
                mark_cancelled(job)
                return

            job.status = JobStatus.RUNNING
            on_job_started(job.id)
            temp_path = self._temp_output_path(job.output_path, job.id)
            self._cleanup_partial(temp_path)

            def progress_hook(percent: int) -> None:
                if on_job_progress:
                    on_job_progress(job.id, max(0, min(percent, 100)))

            try:
                converter.convert(
                    job.input_path,
                    temp_path,
                    job.params,
                    cancel_cb,
                    progress_hook
                )
                if cancel_cb():
                    raise ConversionCancelled()
                if not temp_path.exists() or temp_path.stat().st_size == 0:
                    raise RuntimeError(
                        f"Output file was not created or is empty: {job.output_path.name}"
                    )
                if not job.overwrite and job.output_path.exists():
                    raise RuntimeError(
                        f"Output file already exists: {job.output_path.name}"
                    )
                temp_path.replace(job.output_path)
                progress_hook(100)
                job.status = JobStatus.DONE
                on_job_finished(job.id)
            except ConversionCancelled:
                self._cleanup_partial(temp_path)
                mark_cancelled(job)
            except Exception as e:
                self._cleanup_partial(temp_path)
                job.status = JobStatus.FAILED
                job.error = str(e)
                on_job_failed(job.id, job.error)

        cpu_cores = os.cpu_count() or 4

        for conv_name, jobs in jobs_by_converter.items():
            if cancel_cb():
                for job in jobs:
                    if job.status == JobStatus.PENDING:
                        mark_cancelled(job)
                continue

            converter = converter_map.get(conv_name)
            if not converter:
                for j in jobs:
                    j.status = JobStatus.FAILED
                    j.error = t("Конвертер '{name}' не найден").format(name=conv_name)
                    on_job_failed(j.id, j.error)
                continue

            if conv_name == "ImageConverter":
                workers = cpu_cores
            elif conv_name == "AudioConverter":
                workers = min(4, cpu_cores)
            elif conv_name == "VideoConverter":
                workers = 2
            else:
                workers = 1

            effective_workers = self._effective_workers(workers)
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=effective_workers
            ) as pool:
                futures = [pool.submit(_process_job, job, converter) for job in jobs]

                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()
                    except Exception:
                        pass
