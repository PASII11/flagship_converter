"""Версия приложения: единый источник и синхронизация с pyproject."""
import re
from pathlib import Path

from flagship_converter.version import __version__


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)


def test_version_matches_pyproject():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    match = re.search(
        r'^version = "([^"]+)"', pyproject.read_text(encoding="utf-8"), re.MULTILINE
    )
    assert match is not None
    assert __version__ == match.group(1)
