"""Пресеты конвертации: модель и JSON-хранилище."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, QStandardPaths, Signal

DEFAULT_CODEC = "Авто (CPU x264)"


@dataclass
class Preset:
    id: str
    name: str
    builtin: bool
    formats: dict[str, str] = field(default_factory=dict)
    image_quality: int = 85
    audio_bitrate: str = "192k"
    video_bitrate: str = "2.5M"
    video_codec: str = DEFAULT_CODEC


BUILTIN_PRESETS: list[Preset] = []


def _default_path() -> Path:
    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    return Path(base or ".") / "FlagshipConverter" / "presets.json"


class PresetStore(QObject):
    changed = Signal()

    def __init__(self, path: Path | None = None) -> None:
        super().__init__()
        self._path = path or _default_path()
        self._user: list[Preset] = []
        self._load()

    def presets(self) -> list[Preset]:
        return list(BUILTIN_PRESETS) + list(self._user)

    def user_presets(self) -> list[Preset]:
        return list(self._user)

    def get(self, preset_id: str) -> Preset | None:
        return next((p for p in self.presets() if p.id == preset_id), None)

    def add(self, preset: Preset) -> None:
        self._user.append(preset)
        self._save()
        self.changed.emit()

    def update(self, preset: Preset) -> None:
        if preset.builtin:
            return
        self._user = [preset if p.id == preset.id else p for p in self._user]
        self._save()
        self.changed.emit()

    def delete(self, preset_id: str) -> None:
        existing = self.get(preset_id)
        if existing is None or existing.builtin:
            return
        self._user = [p for p in self._user if p.id != preset_id]
        self._save()
        self.changed.emit()

    def duplicate(self, preset_id: str) -> Preset:
        source = self.get(preset_id)
        if source is None:
            raise KeyError(preset_id)
        copy = Preset(
            id=str(uuid.uuid4()),
            name=f"{source.name} (копия)",
            builtin=False,
            formats=dict(source.formats),
            image_quality=source.image_quality,
            audio_bitrate=source.audio_bitrate,
            video_bitrate=source.video_bitrate,
            video_codec=source.video_codec,
        )
        self.add(copy)
        return copy

    def _load(self) -> None:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._user = [
                Preset(**{**item, "builtin": False})
                for item in raw.get("presets", [])
            ]
        except (OSError, ValueError, TypeError):
            self._user = []

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"version": 1, "presets": [asdict(p) for p in self._user]}
            self._path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass
