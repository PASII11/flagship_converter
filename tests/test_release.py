"""release.py: чтение версии и чексуммы (модуль в корне — грузим по пути)."""
import hashlib
import importlib.util
from pathlib import Path

import pytest

from flagship_converter.version import __version__

_RELEASE_PATH = Path(__file__).resolve().parents[1] / "release.py"
_spec = importlib.util.spec_from_file_location("release", _RELEASE_PATH)
release = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(release)


def test_read_version_matches_package():
    assert release.read_version() == __version__


def test_sha256_file(tmp_path):
    payload = tmp_path / "data.bin"
    payload.write_bytes(b"flagship")
    assert release.sha256_file(payload) == hashlib.sha256(b"flagship").hexdigest()


def test_iss_script_exists():
    assert (Path(__file__).resolve().parents[1] / "packaging" / "installer.iss").exists()


def test_check_dist_stamp_ok(tmp_path):
    (tmp_path / "version.txt").write_text("1.0.0\n", encoding="utf-8")
    release.check_dist_stamp(tmp_path, "1.0.0")


def test_check_dist_stamp_mismatch(tmp_path):
    (tmp_path / "version.txt").write_text("0.9.0\n", encoding="utf-8")
    with pytest.raises(release.ReleaseError):
        release.check_dist_stamp(tmp_path, "1.0.0")


def test_check_dist_stamp_missing(tmp_path):
    with pytest.raises(release.ReleaseError):
        release.check_dist_stamp(tmp_path, "1.0.0")
