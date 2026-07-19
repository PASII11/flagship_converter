"""Проверка обновлений: разбор версий, сравнение, запрос к GitHub API."""
import io
import json
import urllib.error

from flagship_converter.core import update_checker as uc


class TestParseVersion:
    def test_plain(self):
        assert uc.parse_version("1.2.3") == (1, 2, 3)

    def test_v_prefix(self):
        assert uc.parse_version("v1.2.3") == (1, 2, 3)

    def test_two_components(self):
        assert uc.parse_version("v1.2") == (1, 2)

    def test_garbage(self):
        assert uc.parse_version("release-1") is None

    def test_empty(self):
        assert uc.parse_version("") is None

    def test_prerelease_suffix_rejected(self):
        assert uc.parse_version("v1.2.3-beta") is None


class TestIsNewer:
    def test_newer(self):
        assert uc.is_newer("v1.1.0", "1.0.0") is True

    def test_equal(self):
        assert uc.is_newer("v1.0.0", "1.0.0") is False

    def test_older(self):
        assert uc.is_newer("v0.9.9", "1.0.0") is False

    def test_bad_remote_tag(self):
        assert uc.is_newer("nightly", "1.0.0") is False

    def test_defaults_to_app_version(self):
        # с локальной версией по умолчанию сравнение просто не должно падать
        assert uc.is_newer("v0.0.1") is False


class _FakeResponse(io.BytesIO):
    """urlopen возвращает контекст-менеджер с .read() — имитируем его."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class TestFetchLatestTag:
    def test_ok(self, monkeypatch):
        body = json.dumps({"tag_name": "v1.2.0"}).encode()
        monkeypatch.setattr(
            uc.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(body)
        )
        assert uc.fetch_latest_tag() == "v1.2.0"

    def test_network_error(self, monkeypatch):
        def boom(*a, **k):
            raise urllib.error.URLError("offline")

        monkeypatch.setattr(uc.urllib.request, "urlopen", boom)
        assert uc.fetch_latest_tag() is None

    def test_bad_json(self, monkeypatch):
        monkeypatch.setattr(
            uc.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(b"<html>")
        )
        assert uc.fetch_latest_tag() is None

    def test_missing_tag_name(self, monkeypatch):
        body = json.dumps({"name": "no tag here"}).encode()
        monkeypatch.setattr(
            uc.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(body)
        )
        assert uc.fetch_latest_tag() is None
