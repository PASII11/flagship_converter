"""TaskQueue: добавление, bulk-операции, пресеты, override."""
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from flagship_converter.ui.presets import BUILTIN_PRESETS
from flagship_converter.ui.widgets.task_queue import TaskQueue


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _files(tmp_path: Path) -> list[Path]:
    paths = []
    for name in ("a.jpg", "b.jpg", "c.mp3"):
        f = tmp_path / name
        f.write_bytes(b"x")
        paths.append(f)
    return paths


def test_add_files_skips_duplicates(app, tmp_path):
    q = TaskQueue()
    files = _files(tmp_path)
    assert q.add_files(files) == 3
    assert q.add_files(files) == 0
    assert q.count() == 3
    assert q.categories_present() == {"image", "audio"}


def test_bulk_set_format_skips_overridden(app, tmp_path):
    q = TaskQueue()
    q.add_files(_files(tmp_path))
    img_rows = [r for r in q.rows() if r.category == "image"]
    img_rows[0]._format_box.setCurrentText("png")  # ручное изменение
    assert img_rows[0].is_overridden

    changed = q.bulk_set_format("image", "bmp")
    assert changed == 1
    assert img_rows[0].target_ext == "png"
    assert img_rows[1].target_ext == "bmp"


def test_apply_preset_skips_overridden(app, tmp_path):
    q = TaskQueue()
    q.add_files(_files(tmp_path))
    rows = q.rows()
    rows[0]._format_box.setCurrentText("png")
    q.apply_preset(BUILTIN_PRESETS[0])  # «Для веба»: image→webp, audio→mp3
    assert rows[0].target_ext == "png"
    assert rows[1].target_ext == "webp"
    audio = [r for r in rows if r.category == "audio"][0]
    assert audio.target_ext == "mp3"


def test_remove_row_via_signal(app, tmp_path):
    q = TaskQueue()
    q.add_files(_files(tmp_path))
    row = q.rows()[0]
    row.remove_requested.emit(row.card_id)
    assert q.count() == 2
    assert q.get_row(row.card_id) is None
