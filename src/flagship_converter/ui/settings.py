"""Настройки приложения поверх QSettings."""
from __future__ import annotations

from PySide6.QtCore import QLocale, QObject, QSettings, Signal

from flagship_converter.ui.video_codecs import DEFAULT_VIDEO_CODEC, migrate_video_codec

DEFAULT_CODEC = DEFAULT_VIDEO_CODEC


def detect_system_language() -> str:
    return "ru" if QLocale.system().name().startswith("ru") else "en"


class AppSettings(QObject):
    changed = Signal()

    def __init__(self, qsettings: QSettings | None = None) -> None:
        super().__init__()
        self._s = qsettings or QSettings("Flagship", "FlagshipConverter")
        if not self._s.contains("language"):
            self._s.setValue("language", detect_system_language())
            self._s.sync()

    def _set(self, key: str, value: object) -> None:
        self._s.setValue(key, value)
        self._s.sync()
        self.changed.emit()

    @property
    def language(self) -> str:
        value = str(self._s.value("language", "ru"))
        return value if value in ("ru", "en") else "ru"

    @language.setter
    def language(self, value: str) -> None:
        self._set("language", value)

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
        raw = str(self._s.value("default_video_codec", DEFAULT_CODEC))
        return migrate_video_codec(raw)

    @default_video_codec.setter
    def default_video_codec(self, value: str) -> None:
        self._set("default_video_codec", value)
