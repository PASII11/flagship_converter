"""FileRow: категории, форматы, override, статусы."""
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from flagship_converter.core.models import JobStatus
from flagship_converter.ui.presets import Preset
from flagship_converter.ui.widgets.file_row import FileRow, get_category


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _img(tmp_path: Path) -> Path:
    f = tmp_path / "a.jpg"
    f.write_bytes(b"x")
    return f


def test_get_category():
    assert get_category(Path("a.jpg")) == "image"
    assert get_category(Path("a.mp3")) == "audio"
    assert get_category(Path("a.mkv")) == "video"
    assert get_category(Path("a.pdf")) == "doc"
    assert get_category(Path("a.xyz")) == "unknown"


def test_default_format_and_convertible(app, tmp_path):
    row = FileRow(_img(tmp_path))
    assert row.category == "image"
    assert row.is_convertible()
    assert row.target_ext == "webp"
    assert row.is_overridden is False
    assert row._expanded is True


def test_set_target_format_does_not_override(app, tmp_path):
    row = FileRow(_img(tmp_path))
    row.set_target_format("png")
    assert row.target_ext == "png"
    assert row.is_overridden is False


def test_apply_preset_sets_format_and_params(app, tmp_path):
    row = FileRow(_img(tmp_path))
    preset = Preset(
        id="mail", name="Почта", builtin=False,
        formats={"image": "jpg"}, image_quality=70,
    )
    row.apply_preset(preset)
    assert row.target_ext == "jpg"
    assert row.job_params["quality"] == 70


def test_preset_combo_filtered_by_category(app, tmp_path):
    row = FileRow(_img(tmp_path))
    row.set_presets([
        Preset(id="i", name="Img", builtin=False, formats={"image": "png"}),
        Preset(id="v", name="Vid", builtin=False, formats={"video": "mp4"}),
    ])
    assert row._preset_box.count() == 2
    assert row._preset_box.findData("i") == 1
    assert row._preset_box.findData("v") == -1


def test_format_change_resets_done_status(app, tmp_path):
    row = FileRow(_img(tmp_path))
    row.set_status(JobStatus.DONE)
    row._format_box.setCurrentText("png")
    assert row.status == JobStatus.PENDING


def test_error_state(app, tmp_path):
    row = FileRow(_img(tmp_path))
    row.set_error("boom")
    assert row.status == JobStatus.FAILED


def test_unknown_file_not_convertible(app, tmp_path):
    f = tmp_path / "a.xyz"
    f.write_bytes(b"x")
    row = FileRow(f)
    assert not row.is_convertible()
    assert row.target_ext == ""
