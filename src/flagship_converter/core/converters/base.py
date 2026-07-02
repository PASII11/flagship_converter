"""Базовый протокол конвертера."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol


class ConversionCancelled(RuntimeError):
    """Raised when a conversion is cancelled by the user."""


class Converter(Protocol):
    supported_outputs: set[str]

    def can_handle(self, path: Path) -> bool: ...

    def build_output_path(
        self,
        input_path: Path,
        output_dir: Path,
        target_ext: str,
        overwrite: bool,
    ) -> Path: ...

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        params: dict[str, object],
        cancel_cb: Callable[[], bool],
        progress_cb: Callable[[int], None] | None = None,
    ) -> None: ...


def safe_output_path(base: Path, overwrite: bool) -> Path:
    if overwrite or not base.exists():
        return base
    stem = base.stem
    suffix = base.suffix
    parent = base.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
