"""DropOverlay: показ/скрытие и текст."""
import pytest
from PySide6.QtWidgets import QApplication, QWidget

from flagship_converter.ui.widgets.drop_overlay import DropOverlay


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_show_hide(app):
    host = QWidget()
    host.resize(400, 300)
    overlay = DropOverlay(host)
    assert not overlay.isVisibleTo(host)
    overlay.show_overlay("Отпустите, чтобы добавить файлы")
    assert overlay.isVisibleTo(host)
    assert overlay._label.text() == "Отпустите, чтобы добавить файлы"
    assert overlay.geometry() == host.rect()
    overlay.hide_overlay()
    assert not overlay.isVisibleTo(host)
