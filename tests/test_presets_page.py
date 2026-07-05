"""PresetsPage: карточки, редактор, сигнал применения."""
import pytest
from PySide6.QtWidgets import QApplication

from flagship_converter.ui.pages.presets_page import PresetsPage
from flagship_converter.ui.presets import PresetStore


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_no_cards_initially(app, tmp_path):
    page = PresetsPage(PresetStore(tmp_path / "p.json"))
    assert len(page._cards) == 0


def test_new_preset_via_editor(app, tmp_path):
    store = PresetStore(tmp_path / "p.json")
    page = PresetsPage(store)
    page._start_new()
    page._name_edit.setText("Тестовый")
    page._save_editor()
    assert any(p.name == "Тестовый" for p in store.user_presets())
    assert len(page._cards) == 1


def test_editor_saves_only_configured_types(app, tmp_path):
    store = PresetStore(tmp_path / "p.json")
    page = PresetsPage(store)
    page._start_new()
    page._name_edit.setText("Только картинки")
    page._fmt_box.setCurrentText("webp")
    page._save_editor()
    preset = store.user_presets()[0]
    assert preset.formats == {"image": "webp"}


def test_apply_signal(app, tmp_path):
    page = PresetsPage(PresetStore(tmp_path / "p.json"))
    got: list[str] = []
    page.apply_requested.connect(got.append)
    page._on_apply("p1")
    assert got == ["p1"]
