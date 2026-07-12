"""TaskQueue: добавление, bulk-операции, пресеты, override."""
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from flagship_converter.ui.presets import Preset
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
    web = Preset(
        id="web", name="Веб", builtin=False,
        formats={"image": "webp", "audio": "mp3"},
    )
    q.apply_preset(web)
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


def test_pending_count_excludes_done(app, tmp_path):
    from flagship_converter.core.models import JobStatus

    q = TaskQueue()
    q.add_files(_files(tmp_path))
    q.rows()[0].set_status(JobStatus.DONE)
    assert q.convertible_count() == 3
    assert q.pending_count() == 2


def test_default_video_codec_applied_to_new_rows(app, tmp_path):
    q = TaskQueue()
    q.default_video_codec = "nvidia"
    f = tmp_path / "v.mkv"
    f.write_bytes(b"x")
    q.add_files([f])
    row = q.rows()[0]
    assert row.job_params["video_codec"] == "nvidia"
    assert row.is_overridden is False


def test_retranslate_updates_empty_state(app, tmp_path):
    from flagship_converter import i18n

    q = TaskQueue()
    i18n.set_language("en")
    q.retranslate()
    assert q._empty_title.text() == "Drag files or folders here"
    assert q._empty_btn.text() == "Choose files"


def test_add_expanded_files_with_rel(app, tmp_path):
    from flagship_converter.core.expand import ExpandedFile

    root = tmp_path / "photos"
    root.mkdir()
    f = root / "a.jpg"
    f.write_bytes(b"x")
    q = TaskQueue()
    assert q.add_files([ExpandedFile(path=f, source_root=root)]) == 1
    assert q.rows()[0].rel_subdir == Path("photos")


def test_re_drop_file_from_added_folder_dedupes(app, tmp_path):
    from flagship_converter.core.expand import ExpandedFile

    root = tmp_path / "photos"
    root.mkdir()
    f = root / "a.jpg"
    f.write_bytes(b"x")
    q = TaskQueue()
    q.add_files([ExpandedFile(path=f, source_root=root)])
    assert q.add_files([f]) == 0
    assert q.count() == 1


def test_empty_state_has_folder_button(app):
    q = TaskQueue()
    fired = []
    q.add_folder_clicked.connect(lambda: fired.append(1))
    q._empty_folder_btn.click()
    assert fired == [1]
    assert q._empty_title.text() == "Перетащите файлы или папки сюда"
