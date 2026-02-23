"""Модели данных для задач конвертации."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path


class JobStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    DONE = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class ConversionJob:
    """Одна задача конвертации файла."""

    input_path: Path
    output_path: Path
    converter: str
    params: dict[str, object]
    target_ext: str = ""          # ← NEW: каждый job знает свой формат
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    error: str | None = None


@dataclass
class ConversionPlan:
    """Набор задач конвертации, составленный перед запуском."""

    jobs: list[ConversionJob] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.jobs)

    @property
    def done_count(self) -> int:
        return sum(1 for j in self.jobs if j.status == JobStatus.DONE)

    @property
    def failed_count(self) -> int:
        return sum(1 for j in self.jobs if j.status == JobStatus.FAILED)
