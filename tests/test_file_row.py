"""FileRow: категории, форматы, override, статусы."""
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from flagship_converter.core.models import JobStatus
from flagship_converter.ui.presets import Preset
from flagship_converter.ui.widgets.file_row import OUTPUT_FORMATS, FileRow, get_category


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


def test_job_params_video_codec_is_an_id(app, tmp_path):
    f = tmp_path / "v.mkv"
    f.write_bytes(b"x")
    row = FileRow(f)
    assert row.job_params["video_codec"] == "auto"
    row._codec.setCurrentIndex(row._codec.findData("nvidia"))
    assert row.job_params["video_codec"] == "nvidia"


def test_apply_preset_sets_codec_by_id(app, tmp_path):
    f = tmp_path / "v.mkv"
    f.write_bytes(b"x")
    row = FileRow(f)
    preset = Preset(
        id="v1", name="Video", builtin=False,
        formats={"video": "mp4"}, video_codec="intel",
    )
    row.apply_preset(preset)
    assert row.job_params["video_codec"] == "intel"


def test_retranslate_updates_labels_and_error(app, tmp_path):
    from flagship_converter import i18n

    f = tmp_path / "a.jpg"
    f.write_bytes(b"x")
    row = FileRow(f)
    row.set_error("disk full")
    i18n.set_language("en")
    row.retranslate()
    assert row._preset_label.text() == "Preset"
    assert row._quality_label.text() == "Quality"
    assert row._error_label.text() == "Conversion failed: disk full"


def test_retranslate_does_not_mark_row_as_overridden(app, tmp_path):
    from flagship_converter import i18n

    f = tmp_path / "v.mkv"
    f.write_bytes(b"x")
    row = FileRow(f)
    assert row.is_overridden is False
    i18n.set_language("en")
    row.retranslate()
    assert row.is_overridden is False


def test_construct_time_translation(app, tmp_path):
    from flagship_converter import i18n

    i18n.set_language("en")
    f = tmp_path / "a.jpg"
    f.write_bytes(b"x")
    row = FileRow(f)
    assert row._preset_label.text() == "Preset"
    assert "Image" in row._meta.text()


def _video_row(tmp_path):
    f = tmp_path / "v.mp4"
    f.write_bytes(b"x")
    return FileRow(f)


def test_gif_target_shows_gif_controls(app, tmp_path):
    row = _video_row(tmp_path)
    row._format_box.setCurrentText("gif")
    assert row._gif_fps.isVisibleTo(row)
    assert row._gif_width.isVisibleTo(row)
    assert not row._vbitrate.isVisibleTo(row)
    assert not row._codec.isVisibleTo(row)
    assert not row._abitrate.isVisibleTo(row)


def test_audio_target_shows_audio_bitrate(app, tmp_path):
    row = _video_row(tmp_path)
    row._format_box.setCurrentText("mp3")
    assert row._abitrate.isVisibleTo(row)
    assert not row._vbitrate.isVisibleTo(row)
    assert not row._gif_fps.isVisibleTo(row)
    row._format_box.setCurrentText("wav")
    assert not row._abitrate.isVisibleTo(row)


def test_video_target_keeps_video_controls(app, tmp_path):
    row = _video_row(tmp_path)
    row._format_box.setCurrentText("mp4")
    assert row._vbitrate.isVisibleTo(row)
    assert row._codec.isVisibleTo(row)
    assert not row._gif_fps.isVisibleTo(row)
    row._format_box.setCurrentText("webm")
    assert not row._codec.isVisibleTo(row)


def test_job_params_include_gif_settings(app, tmp_path):
    row = _video_row(tmp_path)
    params = row.job_params
    assert params["gif_fps"] == 15
    assert params["gif_width"] == 480
    row._gif_fps.setCurrentText("24")
    row._gif_width.setCurrentIndex(3)  # Оригинал
    params = row.job_params
    assert params["gif_fps"] == 24
    assert params["gif_width"] == 0


def test_rel_subdir_shown_in_meta(app, tmp_path):
    sub = tmp_path / "photos" / "2024"
    sub.mkdir(parents=True)
    f = sub / "a.jpg"
    f.write_bytes(b"x")
    row = FileRow(f, rel_subdir=Path("photos") / "2024")
    assert row.rel_subdir == Path("photos") / "2024"
    assert row._meta.text().startswith("photos/2024 · ")


def test_no_rel_subdir_keeps_meta_format(app, tmp_path):
    f = tmp_path / "a.jpg"
    f.write_bytes(b"x")
    row = FileRow(f)
    assert row.rel_subdir is None
    assert row._meta.text() == "Изображение · 1 B"


def test_retranslate_keeps_rel_prefix(app, tmp_path):
    from flagship_converter import i18n

    f = tmp_path / "a.jpg"
    f.write_bytes(b"x")
    row = FileRow(f, rel_subdir=Path("photos"))
    i18n.set_language("en")
    row.retranslate()
    assert row._meta.text().startswith("photos · Image")


def test_heic_and_avif_are_image_category():
    assert get_category(Path("x.heic")) == "image"
    assert get_category(Path("x.heif")) == "image"
    assert get_category(Path("x.avif")) == "image"


def test_avif_in_image_output_formats():
    assert "avif" in OUTPUT_FORMATS["image"]


def test_size_combo_visible_only_for_video_targets(app, tmp_path):
    row = _video_row(tmp_path)
    row._format_box.setCurrentText("mp4")
    assert row._size_box.isVisibleTo(row)
    assert not row._size_spin.isVisibleTo(row)
    row._format_box.setCurrentText("gif")
    assert not row._size_box.isVisibleTo(row)
    row._format_box.setCurrentText("mp3")
    assert not row._size_box.isVisibleTo(row)


def test_size_preset_hides_manual_bitrate(app, tmp_path):
    row = _video_row(tmp_path)
    assert row._vbitrate.isVisibleTo(row)
    assert row.job_params["target_size_mb"] == 0
    row._size_box.setCurrentIndex(row._size_box.findData(8))
    assert not row._vbitrate.isVisibleTo(row)
    assert row.job_params["target_size_mb"] == 8


def test_custom_size_uses_spinbox(app, tmp_path):
    row = _video_row(tmp_path)
    row._size_box.setCurrentIndex(row._size_box.findData(-1))
    assert row._size_spin.isVisibleTo(row)
    row._size_spin.setValue(123)
    assert row.job_params["target_size_mb"] == 123
