"""MainWindow: навигация, страницы, тема."""
import pytest
from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtWidgets import QApplication

from flagship_converter.core.engine import ConversionEngine
from flagship_converter.ui import theme
from flagship_converter.ui.main_window import MainWindow
from flagship_converter.ui.presets import PresetStore
from flagship_converter.ui.settings import AppSettings


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def window(app, tmp_path):
    QCoreApplication.setOrganizationName("FlagshipTest")
    qs = QSettings("FlagshipTest", "MainWindowTests")
    qs.clear()
    return MainWindow(
        settings=AppSettings(qs),
        store=PresetStore(tmp_path / "p.json"),
        engine=ConversionEngine(),
        check_updates=False,
    )


def test_three_pages_and_nav(window):
    assert window._stack.count() == 3
    assert window._stack.currentIndex() == 0
    window._nav_buttons[2].click()
    assert window._stack.currentIndex() == 2
    window._nav_buttons[0].click()
    assert window._stack.currentIndex() == 0


def test_no_status_bar(window):
    from PySide6.QtWidgets import QStatusBar

    # statusBar() создаёт бар лениво; findChild вернёт None, если его не создавали
    assert window.findChild(QStatusBar) is None


def test_theme_change_via_settings(window):
    window._settings.theme_mode = "dark"
    assert theme.theme_mode() == theme.ThemeMode.DARK
    window._settings.theme_mode = "light"
    assert theme.theme_mode() == theme.ThemeMode.LIGHT


def test_language_change_retranslates_nav(window):
    window._settings.language = "en"
    assert window._nav_buttons[0].text() == "Converter"
    assert window._nav_buttons[2].text() == "Settings"
    window._settings.language = "ru"
    assert window._nav_buttons[0].text() == "Конвертер"


def test_update_button_hidden_initially(window):
    assert window._update_btn.isHidden()
    assert window._update_checker is None  # check_updates=False — сети нет


def test_update_button_appears_with_version(window):
    window._show_update_button("v9.9.9")
    assert not window._update_btn.isHidden()
    assert "v9.9.9" in window._update_btn.text()


def test_update_button_opens_releases_page(window, monkeypatch):
    from PySide6.QtGui import QDesktopServices

    from flagship_converter.core.update_checker import RELEASES_PAGE_URL

    opened = []
    monkeypatch.setattr(
        QDesktopServices, "openUrl", lambda url: opened.append(url.toString()) or True
    )
    window._show_update_button("v9.9.9")
    window._update_btn.click()
    assert opened == [RELEASES_PAGE_URL]
