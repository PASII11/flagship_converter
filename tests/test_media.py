"""Хелпер аргументов аудио-кодирования."""
from flagship_converter.core.converters.media import audio_encode_args


def test_flac_uses_flac_codec():
    assert audio_encode_args("flac", "192k") == ["-c:a", "flac"]


def test_wav_uses_pcm():
    assert audio_encode_args("wav", "192k") == ["-c:a", "pcm_s16le"]


def test_lossy_formats_use_bitrate():
    for ext in ("mp3", "aac", "ogg"):
        assert audio_encode_args(ext, "256k") == ["-b:a", "256k"]
