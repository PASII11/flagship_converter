"""Развёртка входных путей: файлы проходят как есть, папки — рекурсивно."""
from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExpandedFile:
    """Файл после развёртки: сам путь и папка, из которой он пришёл."""

    path: Path
    source_root: Path | None = None

    @property
    def rel_subdir(self) -> Path | None:
        """Подпуть от родителя брошенной папки: включает её имя."""
        if self.source_root is None:
            return None
        try:
            rel = self.path.parent.relative_to(self.source_root.parent)
        except ValueError:
            return None
        return None if rel == Path(".") else rel


def expand_input_paths(
    paths: Iterable[str | Path],
    supported_exts: set[str],
) -> list[ExpandedFile]:
    """Файлы — без фильтра (очередь покажет неподдерживаемые), папки — с фильтром."""
    result: list[ExpandedFile] = []
    for raw in paths:
        try:
            p = Path(raw)
            if p.is_file():
                result.append(ExpandedFile(path=p))
            elif p.is_dir():
                result.extend(_walk_dir(p, supported_exts))
        except OSError:
            continue
    return result


def _walk_dir(root: Path, supported_exts: set[str]) -> list[ExpandedFile]:
    found: list[ExpandedFile] = []
    walker = os.walk(root, onerror=lambda _e: None, followlinks=False)
    for dirpath, dirnames, filenames in walker:
        base = Path(dirpath)
        dirnames[:] = sorted(
            d for d in dirnames
            if not d.startswith(".") and not (base / d).is_junction()
        )
        for name in sorted(filenames):
            file_path = base / name
            if file_path.suffix.lower() in supported_exts:
                found.append(ExpandedFile(path=file_path, source_root=root))
    return found
