"""PresetsPage: карточки, редактор, защита builtin."""
import pytest
from PySide6.QtWidgets import QApplication

from flagship_converter.ui.pages.presets_page import PresetsPage
from flagship_converter.ui.presets import PresetStore


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_lists_builtin_cards(app, tmp_path):
    page = PresetsPage(PresetStore(tmp_path / "p.json"))
    assert len(page._cards) == 3


def test_new_preset_via_editor(app, tmp_path):
    store = PresetStore(tmp_path / "p.json")
    page = PresetsPage(store)
    page._start_new()
    page._name_edit.setText("Тестовый")
    page._save_editor()
    assert any(p.name == "Тестовый" for p in store.user_presets())
    assert len(page._cards) == 4


def test_apply_signal(app, tmp_path):
    page = PresetsPage(PresetStore(tmp_path / "p.json"))
    got: list[str] = []
    page.apply_requested.connect(got.append)
    page._on_apply("builtin-web")
    assert got == ["builtin-web"]
