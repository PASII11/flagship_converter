"""Развёртка входных путей: файлы, папки, фильтры, порядок."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from flagship_converter.core.expand import ExpandedFile, expand_input_paths

EXTS = {".jpg", ".mp3"}


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "photos"
    (root / "2024").mkdir(parents=True)
    (root / ".hidden").mkdir()
    (root / "a.jpg").write_bytes(b"x")
    (root / "2024" / "b.jpg").write_bytes(b"x")
    (root / "2024" / "notes.txt").write_bytes(b"x")
    (root / ".hidden" / "c.jpg").write_bytes(b"x")
    return root


def test_single_file_passes_without_filter(tmp_path):
    f = tmp_path / "readme.xyz"
    f.write_bytes(b"x")
    result = expand_input_paths([f], EXTS)
    assert result == [ExpandedFile(path=f)]
    assert result[0].rel_subdir is None


def test_folder_filters_by_extension(tmp_path):
    root = _tree(tmp_path)
    result = expand_input_paths([root], EXTS)
    assert [e.path.name for e in result] == ["a.jpg", "b.jpg"]
    assert all(e.source_root == root for e in result)


def test_hidden_dirs_skipped(tmp_path):
    root = _tree(tmp_path)
    result = expand_input_paths([root], EXTS)
    assert all(".hidden" not in e.path.parts for e in result)


def test_rel_subdir_includes_root_name(tmp_path):
    root = _tree(tmp_path)
    by_name = {e.path.name: e for e in expand_input_paths([root], EXTS)}
    assert by_name["a.jpg"].rel_subdir == Path("photos")
    assert by_name["b.jpg"].rel_subdir == Path("photos") / "2024"


def test_mixed_files_and_folders(tmp_path):
    root = _tree(tmp_path)
    single = tmp_path / "song.mp3"
    single.write_bytes(b"x")
    result = expand_input_paths([single, root], EXTS)
    assert [e.path.name for e in result] == ["song.mp3", "a.jpg", "b.jpg"]


def test_missing_path_skipped(tmp_path):
    assert expand_input_paths([tmp_path / "nope"], EXTS) == []


def test_deterministic_order(tmp_path):
    root = _tree(tmp_path)
    assert expand_input_paths([root], EXTS) == expand_input_paths([root], EXTS)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="создание симлинков на Windows требует привилегий",
)
def test_dir_symlink_not_followed(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (target / "x.jpg").write_bytes(b"x")
    os.symlink(target, root / "link", target_is_directory=True)
    assert expand_input_paths([root], EXTS) == []


@pytest.mark.skipif(sys.platform != "win32", reason="junction — механизм Windows")
def test_dir_junction_not_followed(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (target / "x.jpg").write_bytes(b"x")
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(root / "link"), str(target)],
        check=True,
        capture_output=True,
    )
    assert expand_input_paths([root], EXTS) == []


def test_rel_subdir_none_for_filesystem_root():
    root = Path(Path.cwd().anchor)
    e = ExpandedFile(path=root / "a.jpg", source_root=root)
    assert e.rel_subdir is None
