"""AppSettings: чтение/запись и значения по умолчанию."""
from PySide6.QtCore import QCoreApplication, QSettings

from flagship_converter.ui.settings import AppSettings


def _mem_settings() -> QSettings:
    QCoreApplication.setOrganizationName("FlagshipTest")
    s = QSettings("FlagshipTest", "UnitTests")
    s.clear()
    return s


def test_defaults():
    s = AppSettings(_mem_settings())
    assert s.theme_mode == "system"
    assert s.output_mode == "beside"
    assert s.fixed_output_dir == ""
    assert s.overwrite is False
    assert s.max_workers == 0
    assert s.default_video_codec == "auto"
    assert s.language in ("ru", "en")


def test_roundtrip_persists_between_instances():
    qs = _mem_settings()
    s = AppSettings(qs)
    s.theme_mode = "dark"
    s.output_mode = "fixed"
    s.fixed_output_dir = "C:/out"
    s.overwrite = True
    s.max_workers = 3

    s2 = AppSettings(QSettings("FlagshipTest", "UnitTests"))
    assert s2.theme_mode == "dark"
    assert s2.output_mode == "fixed"
    assert s2.fixed_output_dir == "C:/out"
    assert s2.overwrite is True
    assert s2.max_workers == 3


def test_changed_signal_emitted():
    s = AppSettings(_mem_settings())
    hits: list[bool] = []
    s.changed.connect(lambda: hits.append(True))
    s.theme_mode = "light"
    assert hits


def test_language_persists_between_instances():
    qs = _mem_settings()
    s = AppSettings(qs)
    s.language = "en"

    s2 = AppSettings(QSettings("FlagshipTest", "UnitTests"))
    assert s2.language == "en"


def test_language_defaults_via_system_locale(monkeypatch):
    from flagship_converter.ui import settings as settings_module

    monkeypatch.setattr(settings_module, "detect_system_language", lambda: "en")
    s = AppSettings(_mem_settings())
    assert s.language == "en"


def test_legacy_default_video_codec_text_is_migrated():
    qs = _mem_settings()
    qs.setValue("default_video_codec", "NVIDIA (NVENC)")
    s = AppSettings(qs)
    assert s.default_video_codec == "nvidia"
