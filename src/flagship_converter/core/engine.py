"""Движок конвертации: сборка плана и выполнение задач."""

from __future__ import annotations

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
            for converter in self._converters:
                if converter.can_handle(file_path):
                    output_path = converter.build_output_path(
                        file_path, output_dir, target_ext, overwrite
                    )
                    plan.jobs.append(
                        ConversionJob(
                            input_path=file_path,
                            output_path=output_path,
                            converter=type(converter).__name__,
                            params=params,
                        )
                    )
                    break

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

        for job in plan.jobs:
            if cancel_cb():
                job.status = JobStatus.CANCELLED
                continue

            converter = converter_map.get(job.converter)
            if converter is None:
                job.status = JobStatus.FAILED
                job.error = f"Конвертер '{job.converter}' не найден"
                on_job_failed(job.id, job.error)
                continue

            job.status = JobStatus.RUNNING
            on_job_started(job.id)

            def make_progress_cb(jid: str) -> Callable[[int], None]:
                def cb(percent: int) -> None:
                    if on_job_progress:
                        on_job_progress(jid, percent)
                return cb

            try:
                converter.convert(
                    job.input_path,
                    job.output_path,
                    job.params,
                    cancel_cb,
                    make_progress_cb(job.id) if on_job_progress else None,
                )
                job.status = JobStatus.DONE
                on_job_finished(job.id)
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
                on_job_failed(job.id, job.error)
