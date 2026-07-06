"""video_codecs: stable codec IDs and legacy display-text migration."""
from flagship_converter.ui.video_codecs import (
    DEFAULT_VIDEO_CODEC,
    VIDEO_CODEC_IDS,
    VIDEO_CODEC_LABELS,
    migrate_video_codec,
)


def test_default_codec_is_a_valid_id():
    assert DEFAULT_VIDEO_CODEC in VIDEO_CODEC_IDS


def test_labels_cover_every_id():
    assert set(VIDEO_CODEC_LABELS) == set(VIDEO_CODEC_IDS)


def test_already_valid_id_passes_through():
    for codec_id in VIDEO_CODEC_IDS:
        assert migrate_video_codec(codec_id) == codec_id


def test_migrates_legacy_display_text():
    assert migrate_video_codec("Авто (CPU x264)") == "auto"
    assert migrate_video_codec("AMD (AMF)") == "amd"
    assert migrate_video_codec("NVIDIA (NVENC)") == "nvidia"
    assert migrate_video_codec("Intel (QSV)") == "intel"


def test_unrecognized_value_falls_back_to_default():
    assert migrate_video_codec("something else") == DEFAULT_VIDEO_CODEC
    assert migrate_video_codec("") == DEFAULT_VIDEO_CODEC
