"""Проверка обновлений через GitHub Releases API.

Один анонимный GET при старте приложения. Любая ошибка (нет сети, таймаут,
rate limit, битый JSON) молча трактуется как «обновления нет» — проверка
никогда не роняет и не блокирует приложение.
"""
from __future__ import annotations

import json
import urllib.request

from PySide6.QtCore import QThread, Signal

from flagship_converter.version import __version__

RELEASES_PAGE_URL = "https://github.com/PASII11/flagship_converter/releases/latest"
_API_URL = "https://api.github.com/repos/PASII11/flagship_converter/releases/latest"
_TIMEOUT_SECONDS = 5.0


def parse_version(tag: str) -> tuple[int, ...] | None:
    """'v1.2.3' или '1.2.3' → (1, 2, 3); None, если формат другой."""
    cleaned = tag.strip().lstrip("vV")
    if not cleaned:
        return None
    numbers: list[int] = []
    for part in cleaned.split("."):
        if not part.isdigit():
            return None
        numbers.append(int(part))
    return tuple(numbers)


def is_newer(remote_tag: str, local_version: str = __version__) -> bool:
    """True, если тег с GitHub новее локальной версии."""
    remote = parse_version(remote_tag)
    local = parse_version(local_version)
    if remote is None or local is None:
        return False
    return remote > local


def fetch_latest_tag() -> str | None:
    """Тег последнего релиза с GitHub; None при любой ошибке."""
    request = urllib.request.Request(
        _API_URL, headers={"Accept": "application/vnd.github+json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    tag = payload.get("tag_name") if isinstance(payload, dict) else None
    return tag if isinstance(tag, str) and tag else None


class UpdateChecker(QThread):
    """Фоновая проверка: эмитит update_available(tag), только если есть новее."""

    update_available = Signal(str)

    def run(self) -> None:
        tag = fetch_latest_tag()
        if tag is not None and is_newer(tag):
            self.update_available.emit(tag)
