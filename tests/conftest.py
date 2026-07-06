"""Shared pytest fixtures: keep global mutable UI state deterministic across tests."""
import pytest

from flagship_converter import i18n


@pytest.fixture(autouse=True)
def _reset_language():
    i18n.set_language("ru")
    yield
    i18n.set_language("ru")
