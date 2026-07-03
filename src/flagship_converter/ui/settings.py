"""Настройки приложения поверх QSettings."""
from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, Signal

DEFAULT_CODEC = "Авто (CPU x264)"


class AppSettings(QObject):
    changed = Signal()

    def __init__(self, qsettings: QSettings | None = None) -> None:
        super().__init__()
        self._s = qsettings or QSettings("Flagship", "FlagshipConverter")

    def _set(self, key: str, value: object) -> None:
        self._s.setValue(key, value)
        self._s.sync()
        self.changed.emit()

    @property
    def theme_mode(self) -> str:
        return str(self._s.value("theme_mode", "system"))

    @theme_mode.setter
    def theme_mode(self, value: str) -> None:
        self._set("theme_mode", value)

    @property
    def output_mode(self) -> str:
        return str(self._s.value("output_mode", "beside"))

    @output_mode.setter
    def output_mode(self, value: str) -> None:
        self._set("output_mode", value)

    @property
    def fixed_output_dir(self) -> str:
        return str(self._s.value("fixed_output_dir", ""))

    @fixed_output_dir.setter
    def fixed_output_dir(self, value: str) -> None:
        self._set("fixed_output_dir", value)

    @property
    def overwrite(self) -> bool:
        return self._s.value("overwrite", False, type=bool)

    @overwrite.setter
    def overwrite(self, value: bool) -> None:
        self._set("overwrite", bool(value))

    @property
    def max_workers(self) -> int:
        return self._s.value("max_workers", 0, type=int)

    @max_workers.setter
    def max_workers(self, value: int) -> None:
        self._set("max_workers", int(value))

    @property
    def default_video_codec(self) -> str:
        return str(self._s.value("default_video_codec", DEFAULT_CODEC))

    @default_video_codec.setter
    def default_video_codec(self, value: str) -> None:
        self._set("default_video_codec", value)
