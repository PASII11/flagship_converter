"""CommandBar: пресеты, счётчик, режим конвертации."""
import pytest
from PySide6.QtWidgets import QApplication

from flagship_converter.ui.presets import BUILTIN_PRESETS
from flagship_converter.ui.widgets.command_bar import CommandBar


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_set_presets_and_selection(app):
    bar = CommandBar()
    bar.set_presets(BUILTIN_PRESETS, current_id="builtin-max")
    assert bar.current_preset_id() == "builtin-max"
    # первый элемент — «Свои настройки» с id ""
    bar._preset_box.setCurrentIndex(0)
    assert bar.current_preset_id() == ""


def test_convert_count_text(app):
    bar = CommandBar()
    bar.set_convert_count(5)
    assert bar._convert_btn.text() == "Конвертировать 5"
    bar.set_convert_count(0)
    assert bar._convert_btn.text() == "Конвертировать"


def test_converting_mode(app):
    bar = CommandBar()
    bar.set_converting(True)
    assert bar._cancel_btn.isVisible() or bar._cancel_btn.isVisibleTo(bar)
    assert not bar._convert_btn.isVisibleTo(bar)
    assert not bar._preset_box.isEnabled()
    bar.set_converting(False)
    assert bar._convert_btn.isVisibleTo(bar)
    assert bar._preset_box.isEnabled()
