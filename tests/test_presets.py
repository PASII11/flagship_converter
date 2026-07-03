"""PresetStore: встроенные пресеты, CRUD, JSON-персистентность."""
from pathlib import Path

from flagship_converter.ui.presets import BUILTIN_PRESETS, Preset, PresetStore


def test_builtins_present(tmp_path: Path):
    store = PresetStore(tmp_path / "presets.json")
    ids = [p.id for p in store.presets()]
    assert ids[:3] == ["builtin-web", "builtin-max", "builtin-mail"]
    assert all(p.builtin for p in BUILTIN_PRESETS)


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


def test_delete_and_builtin_protection(tmp_path: Path):
    store = PresetStore(tmp_path / "presets.json")
    store.add(Preset(id="u2", name="X", builtin=False, formats={"image": "jpg"}))
    store.delete("u2")
    assert store.get("u2") is None
    store.delete("builtin-web")
    assert store.get("builtin-web") is not None


def test_duplicate_builtin(tmp_path: Path):
    store = PresetStore(tmp_path / "presets.json")
    copy = store.duplicate("builtin-web")
    assert copy.builtin is False
    assert copy.id != "builtin-web"
    assert copy.name == "Для веба (копия)"
    assert store.get(copy.id) is not None


def test_corrupt_file_degrades_silently(tmp_path: Path):
    path = tmp_path / "presets.json"
    path.write_text("{broken json", encoding="utf-8")
    store = PresetStore(path)
    assert len(store.presets()) == 3
