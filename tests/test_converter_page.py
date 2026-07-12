"""ConverterPage: связка очереди, пресетов и футера."""
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtWidgets import QApplication

from flagship_converter.core.engine import ConversionEngine
from flagship_converter.ui.pages.converter_page import ConverterPage
from flagship_converter.ui.presets import Preset, PresetStore
from flagship_converter.ui.settings import AppSettings


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def page(app, tmp_path):
    QCoreApplication.setOrganizationName("FlagshipTest")
    qs = QSettings("FlagshipTest", "ConverterPageTests")
    qs.clear()
    return ConverterPage(
        ConversionEngine(),
        AppSettings(qs),
        PresetStore(tmp_path / "presets.json"),
    )


def _files(tmp_path: Path) -> list[str]:
    out = []
    for name in ("a.jpg", "b.mp3"):
        f = tmp_path / name
        f.write_bytes(b"x")
        out.append(str(f))
    return out


def test_add_files_updates_counter(page, tmp_path):
    page.add_files(_files(tmp_path))
    assert page._queue.count() == 2
    assert page._command_bar._convert_btn.text() == "Конвертировать 2"


def test_apply_preset_by_id_applies_to_rows(page, tmp_path):
    page._store.add(Preset(
        id="p1", name="Почта", builtin=False,
        formats={"image": "jpg"}, image_quality=70,
    ))
    f = tmp_path / "c.png"
    f.write_bytes(b"x")
    page.add_files([str(f)])
    row = page._queue.rows()[-1]
    assert row._preset_box.count() == 2
    page.apply_preset_by_id("p1")
    assert row.target_ext == "jpg"
    assert row.job_params["quality"] == 70


def test_footer_aggregates_after_callbacks(page, tmp_path):
    page.add_files(_files(tmp_path))
    rows = page._queue.rows()
    page._job_row_map = {"j1": rows[0].card_id, "j2": rows[1].card_id}
    page._progress_by_job = {"j1": 0, "j2": 0}
    page._on_job_started("j1")
    page._on_job_finished("j1")
    page._on_job_failed("j2", "boom")
    page._on_all_done()
    text = page._footer_label.text()
    assert "Готово 1" in text
    assert "Ошибки 1" in text
    assert page._open_folder_btn.isVisibleTo(page)


def test_folder_chip_follows_settings(page):
    page._settings.output_mode = "fixed"
    page._settings.fixed_output_dir = "C:/out"
    assert page._command_bar._folder_btn.text() == "C:/out"


def test_construct_time_translation(app, tmp_path):
    from flagship_converter import i18n

    QCoreApplication.setOrganizationName("FlagshipTest")
    qs = QSettings("FlagshipTest", "ConverterPageEnTests")
    qs.clear()
    i18n.set_language("en")
    page = ConverterPage(
        ConversionEngine(), AppSettings(qs), PresetStore(tmp_path / "presets.json"),
    )
    assert page._footer_label.text() == "Add files or folders, or drag them into the window"


def test_retranslate_updates_footer_and_children(page):
    from flagship_converter import i18n

    i18n.set_language("en")
    page.retranslate()
    assert page._command_bar._add_btn.text() == "Add files"
    assert page._footer_label.text() == "Add files or folders, or drag them into the window"


def test_add_folder_expands_recursively(page, tmp_path):
    root = tmp_path / "photos"
    (root / "2024").mkdir(parents=True)
    (root / "2024" / "a.jpg").write_bytes(b"x")
    (root / "readme.txt").write_bytes(b"x")
    page.add_files([str(root)])
    assert page._queue.count() == 1
    assert page._queue.rows()[0].rel_subdir == Path("photos") / "2024"


def test_output_dir_fixed_preserves_structure(page, tmp_path):
    page._settings.output_mode = "fixed"
    page._settings.fixed_output_dir = str(tmp_path / "out")
    root = tmp_path / "photos"
    root.mkdir()
    (root / "a.jpg").write_bytes(b"x")
    page.add_files([str(root)])
    row = page._queue.rows()[0]
    assert page._output_dir_for(row) == tmp_path / "out" / "photos"


def test_output_dir_beside_unchanged(page, tmp_path):
    f = tmp_path / "a.jpg"
    f.write_bytes(b"x")
    page.add_files([str(f)])
    row = page._queue.rows()[0]
    assert page._output_dir_for(row) == tmp_path / "converted"


def test_folder_without_supported_files_sets_footer(page, tmp_path):
    root = tmp_path / "docs_only"
    root.mkdir()
    (root / "readme.txt").write_bytes(b"x")
    page.add_files([str(root)])
    assert page._queue.count() == 0
    assert page._footer_label.text() == "В папке не найдено поддерживаемых файлов"


def test_large_drop_requires_confirmation(page, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    root = tmp_path / "big"
    root.mkdir()
    for i in range(501):
        (root / f"f{i:03}.jpg").write_bytes(b"x")
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No),
    )
    page.add_files([str(root)])
    assert page._queue.count() == 0
