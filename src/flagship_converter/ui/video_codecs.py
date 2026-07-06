"""Stable video codec identifiers shared by settings, presets, and codec combo boxes.

Display text is translated at the UI layer via i18n.t(VIDEO_CODEC_LABELS[id]);
this module only defines the stable IDs and the Russian source labels.
"""
from __future__ import annotations

VIDEO_CODEC_IDS: list[str] = ["auto", "amd", "nvidia", "intel"]
DEFAULT_VIDEO_CODEC = "auto"

VIDEO_CODEC_LABELS: dict[str, str] = {
    "auto": "Авто (CPU x264)",
    "amd": "AMD (AMF)",
    "nvidia": "NVIDIA (NVENC)",
    "intel": "Intel (QSV)",
}

_LEGACY_LABEL_TO_ID: dict[str, str] = {
    label: codec_id for codec_id, label in VIDEO_CODEC_LABELS.items()
}


def migrate_video_codec(value: str) -> str:
    if value in VIDEO_CODEC_IDS:
        return value
    if value in _LEGACY_LABEL_TO_ID:
        return _LEGACY_LABEL_TO_ID[value]
    if "AMD" in value:
        return "amd"
    if "NVIDIA" in value:
        return "nvidia"
    if "Intel" in value:
        return "intel"
    return DEFAULT_VIDEO_CODEC
