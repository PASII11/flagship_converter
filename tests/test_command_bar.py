"""CommandBar: счётчик и режим конвертации."""
import pytest
from PySide6.QtWidgets import QApplication

from flagship_converter.ui.widgets.command_bar import CommandBar


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_convert_count_text(app):
    bar = CommandBar()
    bar.set_convert_count(5)
    assert bar._convert_btn.text() == "Конвертировать 5"
    bar.set_convert_count(0)
    assert bar._convert_btn.text() == "Конвертировать"


def test_converting_mode(app):
    bar = CommandBar()
    bar.set_converting(True)
    assert bar._cancel_btn.isVisibleTo(bar)
    assert not bar._convert_btn.isVisibleTo(bar)
    assert not bar._add_btn.isEnabled()
    bar.set_converting(False)
    assert bar._convert_btn.isVisibleTo(bar)
    assert bar._add_btn.isEnabled()


def test_retranslate_updates_all_text(app):
    from flagship_converter import i18n

    bar = CommandBar()
    bar.set_convert_count(3)
    i18n.set_language("en")
    bar.retranslate()
    assert bar._add_btn.text() == "Add files"
    assert bar._convert_btn.text() == "Convert 3"
    assert bar._cancel_btn.text() == "Cancel"


def test_construct_time_translation(app):
    from flagship_converter import i18n

    i18n.set_language("en")
    bar = CommandBar()
    assert bar._add_btn.text() == "Add files"
    assert bar._convert_btn.text() == "Convert"


def test_add_folder_button_emits_signal(app):
    bar = CommandBar()
    fired = []
    bar.add_folder_clicked.connect(lambda: fired.append(1))
    bar._add_folder_btn.click()
    assert fired == [1]


def test_add_folder_disabled_while_converting(app):
    bar = CommandBar()
    bar.set_converting(True)
    assert not bar._add_folder_btn.isEnabled()
    bar.set_converting(False)
    assert bar._add_folder_btn.isEnabled()


def test_add_folder_retranslates(app):
    from flagship_converter import i18n

    bar = CommandBar()
    i18n.set_language("en")
    bar.retranslate()
    assert bar._add_folder_btn.text() == "Add folder"
