"""release.py: чтение версии и чексуммы (модуль в корне — грузим по пути)."""
import hashlib
import importlib.util
from pathlib import Path

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
