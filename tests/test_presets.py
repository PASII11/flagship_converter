"""PresetStore: CRUD и JSON-персистентность."""
from pathlib import Path

from flagship_converter.ui.presets import BUILTIN_PRESETS, Preset, PresetStore


def test_no_builtin_presets(tmp_path: Path):
    assert BUILTIN_PRESETS == []
    store = PresetStore(tmp_path / "presets.json")
    assert store.presets() == []


def test_add_persists_and_reloads(tmp_path: Path):
    path = tmp_path / "presets.json"
    store = PresetStore(path)
    preset = Preset(
        id="u1", name="Мой", builtin=False,
        formats={"image": "png", "audio": "wav", "video": "mkv", "doc": "md"},
    )
    store.add(preset)
    assert path.exists()

    store2 = PresetStore(path)
    loaded = store2.get("u1")
    assert loaded is not None
    assert loaded.name == "Мой"
    assert loaded.formats["image"] == "png"


def test_delete_user_preset(tmp_path: Path):
    store = PresetStore(tmp_path / "presets.json")
    store.add(Preset(id="u2", name="X", builtin=False, formats={"image": "jpg"}))
    store.delete("u2")
    assert store.get("u2") is None
    store.delete("missing")
    assert store.presets() == []


def test_duplicate_user_preset(tmp_path: Path):
    store = PresetStore(tmp_path / "presets.json")
    store.add(Preset(id="u3", name="Base", builtin=False, formats={"image": "png"}))
    copy = store.duplicate("u3")
    assert copy.builtin is False
    assert copy.id != "u3"
    assert copy.name == "Base (копия)"
    assert store.get(copy.id) is not None


def test_corrupt_file_degrades_silently(tmp_path: Path):
    path = tmp_path / "presets.json"
    path.write_text("{broken json", encoding="utf-8")
    store = PresetStore(path)
    assert store.presets() == []
