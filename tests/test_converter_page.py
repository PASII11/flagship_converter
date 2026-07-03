"""ConverterPage: связка очереди, bulk-чипов, пресетов и футера."""
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtWidgets import QApplication

from flagship_converter.core.engine import ConversionEngine
from flagship_converter.ui.pages.converter_page import ConverterPage
from flagship_converter.ui.presets import PresetStore
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


def test_add_files_updates_counter_and_chips(page, tmp_path):
    page.add_files(_files(tmp_path))
    assert page._queue.count() == 2
    assert page._command_bar._convert_btn.text() == "Конвертировать 2"
    assert set(page._bulk_chips.keys()) == {"image", "audio"}


def test_preset_applies_to_new_files(page, tmp_path):
    page.apply_preset_by_id("builtin-mail")  # image -> jpg
    f = tmp_path / "c.png"
    f.write_bytes(b"x")
    page.add_files([str(f)])
    row = page._queue.rows()[-1]
    assert row.target_ext == "jpg"


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
