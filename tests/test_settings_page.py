"""SettingsPage: двусторонняя связь с AppSettings."""
import pytest
from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtWidgets import QApplication

from flagship_converter.ui.pages.settings_page import SettingsPage
from flagship_converter.ui.settings import AppSettings


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def settings():
    QCoreApplication.setOrganizationName("FlagshipTest")
    qs = QSettings("FlagshipTest", "SettingsPageTests")
    qs.clear()
    return AppSettings(qs)


def test_widgets_reflect_settings(app, settings):
    settings.theme_mode = "dark"
    settings.max_workers = 4
    settings.overwrite = True
    page = SettingsPage(settings)
    assert page._theme_box.currentData() == "dark"
    assert page._workers_spin.value() == 4
    assert page._conflict_box.currentData() is True


def test_changing_widgets_updates_settings(app, settings):
    page = SettingsPage(settings)
    page._theme_box.setCurrentIndex(page._theme_box.findData("light"))
    assert settings.theme_mode == "light"
    page._workers_spin.setValue(2)
    assert settings.max_workers == 2
    page._output_mode_box.setCurrentIndex(
        page._output_mode_box.findData("fixed")
    )
    assert settings.output_mode == "fixed"
