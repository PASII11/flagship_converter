# GitHub Release & Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Оформить публичный репозиторий: README + MIT-лицензия, установщик и portable-ZIP на GitHub Releases через `release.py`, проверка обновлений в приложении.

**Architecture:** Версия живёт в одном месте (`version.py`). `release.py` локально собирает артефакты (build.py → ZIP + Inno Setup) и публикует релиз через gh CLI. Приложение при старте фоновым QThread спрашивает GitHub API о последнем релизе и показывает кнопку «Доступно обновление» в топ-баре.

**Tech Stack:** Python 3.12, uv, PySide6, PyInstaller, Inno Setup 6, gh CLI, stdlib `urllib`.

**Спека:** `docs/superpowers/specs/2026-07-19-github-release-design.md`

## Global Constraints

- Тесты запускаются: `uv run python -m pytest` (весь набор) или `uv run python -m pytest tests/<файл> -v`.
- Новых runtime-зависимостей НЕ добавлять: проверка обновлений — только stdlib (`urllib.request`, `json`).
- Строки UI: русский исходник + перевод в `_TRANSLATIONS` в `src/flagship_converter/i18n.py` (плоский словарь RU→EN).
- Docstrings и комментарии в коде — на русском, как в остальном репозитории.
- Коммиты: английский conventional style (`feat:`, `chore:`, `docs:`). **Запрещены любые трейлеры Co-Authored-By и упоминания ИИ в коммитах.**
- Версия: единственный источник `src/flagship_converter/version.py`; `pyproject.toml` синхронен; первый релиз — `1.0.0`.
- Репозиторий: `https://github.com/PASII11/flagship_converter` (origin уже настроен).
- Пуш в origin и публикация релиза — только в Task 6, после подтверждения пользователя.

---

### Task 1: Единый источник версии, MIT-лицензия, гигиена .gitignore

**Files:**
- Create: `src/flagship_converter/version.py`
- Create: `tests/test_version.py`
- Create: `LICENSE`
- Modify: `pyproject.toml:3` (version 0.1.0 → 1.0.0)
- Modify: `src/flagship_converter/app.py` (использовать `__version__`)
- Modify: `.gitignore` (docling_models, release/)

**Interfaces:**
- Produces: `flagship_converter.version.__version__: str` — используется в Task 2 (сравнение версий), Task 4 (release.py читает файл регексом `__version__ = "([^"]+)"`).

- [ ] **Step 1: Написать падающий тест**

Создать `tests/test_version.py`:

```python
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
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `uv run python -m pytest tests/test_version.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'flagship_converter.version'`

- [ ] **Step 3: Реализация**

Создать `src/flagship_converter/version.py`:

```python
"""Единственный источник версии приложения.

release.py читает этот файл регексом — формат строки не менять.
"""
__version__ = "1.0.0"
```

В `pyproject.toml` заменить строку 3:

```toml
version = "1.0.0"
```

В `src/flagship_converter/app.py` добавить импорт и заменить хардкод версии:

```python
from flagship_converter.ui.main_window import MainWindow
from flagship_converter.version import __version__
```

и в `main()`:

```python
    app.setApplicationVersion(__version__)
```

- [ ] **Step 4: Прогнать тесты**

Run: `uv run python -m pytest tests/test_version.py -v`
Expected: 2 passed

- [ ] **Step 5: LICENSE и .gitignore**

Создать `LICENSE` (ровно этот текст):

```text
MIT License

Copyright (c) 2026 PASII11

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

В конец `.gitignore` добавить:

```gitignore

# Скачанные модели docling (кладёт build.py, >1 ГБ)
build_tools/docling_models/

# Артефакты релиза (release.py)
release/
```

Примечание: `build_tools/*.exe` уже отслеживаются в git — их НЕ трогать.

- [ ] **Step 6: Прогнать весь набор тестов**

Run: `uv run python -m pytest`
Expected: все тесты зелёные (текущий набор + 2 новых)

- [ ] **Step 7: Commit**

```bash
git add src/flagship_converter/version.py tests/test_version.py LICENSE pyproject.toml src/flagship_converter/app.py .gitignore
git commit -m "chore: add MIT license and single-source app version"
```

---

### Task 2: Модуль проверки обновлений (core)

**Files:**
- Create: `src/flagship_converter/core/update_checker.py`
- Test: `tests/test_update_checker.py`

**Interfaces:**
- Consumes: `flagship_converter.version.__version__` (Task 1).
- Produces (используется в Task 3):
  - `RELEASES_PAGE_URL: str` — страница релизов для открытия в браузере.
  - `parse_version(tag: str) -> tuple[int, ...] | None`
  - `is_newer(remote_tag: str, local_version: str = __version__) -> bool`
  - `fetch_latest_tag() -> str | None` — сетевой вызов, любая ошибка → `None`.
  - `class UpdateChecker(QThread)` с сигналом `update_available = Signal(str)` (аргумент — тег, например `"v1.1.0"`). `run()` эмитит сигнал только если есть более новая версия.

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_update_checker.py`:

```python
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
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `uv run python -m pytest tests/test_update_checker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'flagship_converter.core.update_checker'`

- [ ] **Step 3: Реализация**

Создать `src/flagship_converter/core/update_checker.py`:

```python
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
```

- [ ] **Step 4: Прогнать тесты**

Run: `uv run python -m pytest tests/test_update_checker.py -v`
Expected: 15 passed

- [ ] **Step 5: Commit**

```bash
git add src/flagship_converter/core/update_checker.py tests/test_update_checker.py
git commit -m "feat: add update checker against github releases api"
```

---

### Task 3: Кнопка «Доступно обновление» в главном окне

**Files:**
- Modify: `src/flagship_converter/i18n.py` (новая строка перевода)
- Modify: `src/flagship_converter/ui/main_window.py`
- Test: `tests/test_main_window.py` (фикстура + 3 новых теста)

**Interfaces:**
- Consumes (Task 2): `UpdateChecker` (сигнал `update_available: Signal(str)`), `RELEASES_PAGE_URL`.
- Produces: `MainWindow(..., check_updates: bool = True)`; методы `_show_update_button(tag: str)`, `_open_releases_page()`; атрибуты `_update_btn: QPushButton`, `_update_tag: str | None`, `_update_checker: UpdateChecker | None`. Тесты и app.py полагаются на параметр `check_updates`.

- [ ] **Step 1: Обновить фикстуру и написать падающие тесты**

В `tests/test_main_window.py` заменить фикстуру `window` (строки 18–27) на:

```python
@pytest.fixture()
def window(app, tmp_path):
    QCoreApplication.setOrganizationName("FlagshipTest")
    qs = QSettings("FlagshipTest", "MainWindowTests")
    qs.clear()
    return MainWindow(
        settings=AppSettings(qs),
        store=PresetStore(tmp_path / "p.json"),
        engine=ConversionEngine(),
        check_updates=False,
    )
```

В конец файла добавить:

```python
def test_update_button_hidden_initially(window):
    assert window._update_btn.isHidden()
    assert window._update_checker is None  # check_updates=False — сети нет


def test_update_button_appears_with_version(window):
    window._show_update_button("v9.9.9")
    assert not window._update_btn.isHidden()
    assert "v9.9.9" in window._update_btn.text()


def test_update_button_opens_releases_page(window, monkeypatch):
    from PySide6.QtGui import QDesktopServices

    from flagship_converter.core.update_checker import RELEASES_PAGE_URL

    opened = []
    monkeypatch.setattr(
        QDesktopServices, "openUrl", lambda url: opened.append(url.toString()) or True
    )
    window._show_update_button("v9.9.9")
    window._update_btn.click()
    assert opened == [RELEASES_PAGE_URL]
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `uv run python -m pytest tests/test_main_window.py -v`
Expected: FAIL — `TypeError: MainWindow.__init__() got an unexpected keyword argument 'check_updates'`

- [ ] **Step 3: Перевод в i18n**

В `src/flagship_converter/i18n.py` в секцию `# main_window.py` словаря `_TRANSLATIONS` (после строки `"Отпустите, чтобы добавить файлы": "Drop to add files",`) добавить:

```python
    "Доступно обновление {version}": "Update available {version}",
```

- [ ] **Step 4: Реализация в MainWindow**

В `src/flagship_converter/ui/main_window.py`:

Импорты — заменить строку `from PySide6.QtCore import Qt` и блок QtGui (порядок именно такой, иначе ruff I001):

```python
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QCloseEvent, QDesktopServices, QDragEnterEvent, QDropEvent
```

и сразу после строки `from flagship_converter.core.engine import ConversionEngine` добавить:

```python
from flagship_converter.core.update_checker import RELEASES_PAGE_URL, UpdateChecker
```

Сигнатура `__init__` — добавить параметр после `engine`:

```python
    def __init__(
        self,
        settings: AppSettings | None = None,
        store: PresetStore | None = None,
        engine: ConversionEngine | None = None,
        check_updates: bool = True,
    ) -> None:
```

В конец `__init__` (после `self._apply_theme()`):

```python
        self._update_checker: UpdateChecker | None = None
        if check_updates:
            self._update_checker = UpdateChecker(self)
            self._update_checker.update_available.connect(self._show_update_button)
            self._update_checker.start()
```

В `_build_ui`, перед созданием `self._theme_btn` (строка `self._theme_btn = QPushButton()`), вставить:

```python
        self._update_tag: str | None = None
        self._update_btn = QPushButton()
        self._update_btn.setFixedHeight(34)
        self._update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_btn.clicked.connect(self._open_releases_page)
        self._update_btn.hide()
        bar.addWidget(self._update_btn)
```

Новые методы (после `_cycle_theme`):

```python
    def _show_update_button(self, tag: str) -> None:
        self._update_tag = tag
        self._update_btn.setText(
            t("Доступно обновление {version}").format(version=tag)
        )
        self._update_btn.setStyleSheet(theme.primary_button_qss(theme.palette()))
        self._update_btn.show()

    def _open_releases_page(self) -> None:
        QDesktopServices.openUrl(QUrl(RELEASES_PAGE_URL))
```

В `_apply_theme` (рядом со стилизацией `self._theme_btn`) добавить:

```python
        self._update_btn.setStyleSheet(theme.primary_button_qss(p))
```

В `_retranslate` добавить:

```python
        if self._update_tag is not None:
            self._update_btn.setText(
                t("Доступно обновление {version}").format(version=self._update_tag)
            )
```

Новый `closeEvent` (перед `dragEnterEvent`) — не дать потоку пережить окно:

```python
    def closeEvent(self, event: QCloseEvent) -> None:
        # Поток живёт максимум ~таймаут запроса (5 с); дожидаемся, чтобы Qt
        # не уничтожил работающий QThread.
        if self._update_checker is not None and self._update_checker.isRunning():
            self._update_checker.wait(7000)
        super().closeEvent(event)
```

- [ ] **Step 5: Прогнать тесты**

Run: `uv run python -m pytest tests/test_main_window.py -v`
Expected: все PASS (4 старых + 3 новых)

Run: `uv run python -m pytest`
Expected: весь набор зелёный

- [ ] **Step 6: Commit**

```bash
git add src/flagship_converter/i18n.py src/flagship_converter/ui/main_window.py tests/test_main_window.py
git commit -m "feat: show update-available button in top bar"
```

---

### Task 4: Inno Setup скрипт и release.py

**Files:**
- Create: `packaging/installer.iss`
- Create: `release.py` (корень репозитория)
- Test: `tests/test_release.py`

**Interfaces:**
- Consumes: `src/flagship_converter/version.py` (регекс `__version__ = "([^"]+)"`), `build.py` (существующий, кладёт сборку в `dist/FlagshipConverter/`), `pyproject.toml`.
- Produces: команда `uv run python release.py [--skip-build] [--dry-run] [--notes "..."]`; артефакты в `release/`: `FlagshipConverter-Setup-<v>.exe`, `FlagshipConverter-<v>-portable-win64.zip`, `SHA256SUMS.txt`. Функции `read_version()`, `sha256_file(path)`, `find_iscc()` — тестируются напрямую.

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_release.py`:

```python
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
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `uv run python -m pytest tests/test_release.py -v`
Expected: FAIL — `FileNotFoundError` при загрузке `release.py`

- [ ] **Step 3: Создать packaging/installer.iss**

```ini
; Установщик Flagship Converter.
; Компилируется из release.py:  ISCC /DAppVersion=<версия> packaging\installer.iss
; AppId фиксированный — новые версии ставятся поверх старой установки.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{8A7C0D2E-4B1F-4E9A-9C3D-6F5E2A718B4C}
AppName=Flagship Converter
AppVersion={#AppVersion}
AppPublisher=PASII11
AppPublisherURL=https://github.com/PASII11/flagship_converter
AppSupportURL=https://github.com/PASII11/flagship_converter/issues
DefaultDirName={autopf}\Flagship Converter
DefaultGroupName=Flagship Converter
UninstallDisplayIcon={app}\FlagshipConverter.exe
Compression=lzma2
SolidCompression=yes
OutputDir=..\release
OutputBaseFilename=FlagshipConverter-Setup-{#AppVersion}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\FlagshipConverter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Flagship Converter"; Filename: "{app}\FlagshipConverter.exe"
Name: "{autodesktop}\Flagship Converter"; Filename: "{app}\FlagshipConverter.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\FlagshipConverter.exe"; Description: "{cm:LaunchProgram,Flagship Converter}"; Flags: nowait postinstall skipifsilent
```

- [ ] **Step 4: Создать release.py**

```python
"""Собрать артефакты релиза и опубликовать GitHub Release.

Запуск: uv run python release.py [--skip-build] [--dry-run] [--notes "..."]

Требования на машине сборки:
- Inno Setup 6:  winget install JRSoftware.InnoSetup
- gh CLI:        winget install GitHub.cli  +  gh auth login
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DIST_DIR = REPO_ROOT / "dist" / "FlagshipConverter"
RELEASE_DIR = REPO_ROOT / "release"
ISS_SCRIPT = REPO_ROOT / "packaging" / "installer.iss"

_ISCC_DEFAULTS = [
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
]


class ReleaseError(RuntimeError):
    """Ошибка релиза с понятным пользователю сообщением."""


def read_version() -> str:
    version_file = REPO_ROOT / "src" / "flagship_converter" / "version.py"
    match = re.search(
        r'__version__ = "([^"]+)"', version_file.read_text(encoding="utf-8")
    )
    if not match:
        raise ReleaseError("Не нашёл __version__ в src/flagship_converter/version.py")
    version = match.group(1)
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    py_match = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
    if not py_match or py_match.group(1) != version:
        found = py_match.group(1) if py_match else "не найдена"
        raise ReleaseError(
            f"Версии расходятся: version.py={version}, pyproject.toml={found}"
        )
    return version


def find_iscc() -> Path:
    found = shutil.which("ISCC")
    if found:
        return Path(found)
    for candidate in _ISCC_DEFAULTS:
        if candidate.exists():
            return candidate
    raise ReleaseError(
        "Inno Setup не найден. Установите: winget install JRSoftware.InnoSetup"
    )


def find_gh() -> Path:
    found = shutil.which("gh")
    if not found:
        raise ReleaseError(
            "gh CLI не найден. Установите: winget install GitHub.cli, затем gh auth login"
        )
    return Path(found)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(cmd: list) -> None:
    print("+", " ".join(str(part) for part in cmd), flush=True)
    subprocess.run([str(part) for part in cmd], check=True)


def check_preconditions(version: str) -> None:
    status = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
    ).stdout.strip()
    if status:
        raise ReleaseError("Рабочее дерево не чистое — закоммитьте изменения")
    tag = f"v{version}"
    remote_tags = subprocess.run(
        ["git", "ls-remote", "--tags", "origin", tag],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if remote_tags:
        raise ReleaseError(f"Тег {tag} уже есть на origin — поднимите версию")
    find_iscc()
    find_gh()
    auth = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    if auth.returncode != 0:
        raise ReleaseError("gh не авторизован — выполните: gh auth login")


def build_app() -> None:
    run([sys.executable, "build.py"])
    exe = DIST_DIR / "FlagshipConverter.exe"
    if not exe.exists():
        raise ReleaseError(f"Сборка не создала {exe}")


def make_zip(version: str) -> Path:
    base_name = RELEASE_DIR / f"FlagshipConverter-{version}-portable-win64"
    print(f"Пакую portable ZIP → {base_name}.zip (несколько минут)", flush=True)
    archive = shutil.make_archive(
        str(base_name), "zip", root_dir=DIST_DIR.parent, base_dir=DIST_DIR.name
    )
    return Path(archive)


def make_installer(version: str) -> Path:
    run([find_iscc(), f"/DAppVersion={version}", ISS_SCRIPT])
    installer = RELEASE_DIR / f"FlagshipConverter-Setup-{version}.exe"
    if not installer.exists():
        raise ReleaseError(f"ISCC не создал {installer}")
    return installer


def write_checksums(artifacts: list[Path]) -> Path:
    sums = RELEASE_DIR / "SHA256SUMS.txt"
    lines = [f"{sha256_file(artifact)}  {artifact.name}" for artifact in artifacts]
    sums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sums


def publish(version: str, artifacts: list[Path], notes: str) -> None:
    tag = f"v{version}"
    run(["git", "tag", tag])
    run(["git", "push", "origin", tag])
    run([
        "gh", "release", "create", tag,
        *artifacts,
        "--title", f"Flagship Converter {version}",
        "--notes", notes,
    ])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Сборка и публикация релиза Flagship Converter"
    )
    parser.add_argument(
        "--skip-build", action="store_true", help="использовать готовый dist/"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="только проверки, без сборки и публикации"
    )
    parser.add_argument("--notes", default="", help="текст заметок релиза")
    args = parser.parse_args()

    version = read_version()
    check_preconditions(version)
    print(f"Версия {version}: все проверки пройдены")
    if args.dry_run:
        print("dry-run: сборка и публикация пропущены")
        return

    RELEASE_DIR.mkdir(exist_ok=True)
    if not args.skip_build:
        build_app()
    elif not (DIST_DIR / "FlagshipConverter.exe").exists():
        raise ReleaseError("--skip-build указан, но dist/FlagshipConverter не найден")

    zip_path = make_zip(version)
    installer = make_installer(version)
    sums = write_checksums([installer, zip_path])
    publish(
        version,
        [installer, zip_path, sums],
        args.notes or f"Flagship Converter {version}",
    )
    print(f"Релиз v{version} опубликован: см. страницу Releases на GitHub")


if __name__ == "__main__":
    try:
        main()
    except ReleaseError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as error:
        print(f"Команда завершилась с ошибкой: {error}", file=sys.stderr)
        sys.exit(1)
```

- [ ] **Step 5: Прогнать тесты**

Run: `uv run python -m pytest tests/test_release.py -v`
Expected: 3 passed

Run: `uv run python -m pytest`
Expected: весь набор зелёный

- [ ] **Step 6: Commit**

```bash
git add packaging/installer.iss release.py tests/test_release.py
git commit -m "feat: add release script and inno setup installer"
```

---

### Task 5: README со скриншотом

**Files:**
- Create: `README.md`
- Create: `docs/assets/screenshot.png` (генерируется скриптом ниже)

**Interfaces:**
- Consumes: `MainWindow(check_updates=False)` из Task 3 (для скриншота).
- Produces: README, на который ссылаются страница репозитория и релизы.

- [ ] **Step 1: Сгенерировать скриншот**

```bash
mkdir -p docs/assets
uv run python - <<'EOF'
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from flagship_converter.ui.main_window import MainWindow

app = QApplication([])
window = MainWindow(check_updates=False)
window.resize(1280, 800)
window.show()


def grab() -> None:
    window.grab().save("docs/assets/screenshot.png")
    app.quit()


QTimer.singleShot(600, grab)
app.exec()
EOF
```

Expected: файл `docs/assets/screenshot.png` создан (окно с пустой очередью — норм для v1).
Проверка: `ls -la docs/assets/screenshot.png` — размер > 10 КБ.

- [ ] **Step 2: Создать README.md**

Ровно этот текст (список форматов сверен с `SUPPORTED_INPUT`/`SUPPORTED_OUTPUT` конвертеров):

````markdown
# Flagship Converter

Privacy-first file converter for Windows. Everything runs locally on your
machine — no uploads, no accounts, no telemetry.

![Flagship Converter](docs/assets/screenshot.png)

## Features

- **Images** — convert PNG, JPEG, WebP, BMP, TIFF, AVIF (opens HEIC/HEIF and
  GIF too), with per-file quality control.
- **Video** — convert MP4, MKV, AVI, MOV, WebM, FLV, M4V; compress to an exact
  target file size (fit any upload limit), extract audio (MP3, WAV, FLAC, AAC,
  OGG) or turn clips into GIFs.
- **Audio** — convert MP3, WAV, FLAC, AAC, M4A, OGG, WMA.
- **Documents** — PDF ↔ DOCX ↔ Markdown with layout-aware parsing and built-in
  OCR, so scanned PDFs work too.
- **Batch queue** — drop files or whole folders, convert in parallel, per-file
  settings and reusable presets.
- **Desktop-grade UX** — light/dark theme, English and Russian interface.

## Download

Get the latest version from the
[Releases page](https://github.com/PASII11/flagship_converter/releases/latest):

| File | What it is |
| --- | --- |
| `FlagshipConverter-Setup-<version>.exe` | Installer — recommended. Start menu shortcut, in-place upgrades, uninstaller. |
| `FlagshipConverter-<version>-portable-win64.zip` | Portable build — unzip anywhere and run `FlagshipConverter.exe`. |

**System requirements:** Windows 10/11 x64, ~3 GB of free disk space. FFmpeg,
OCR models and document parsers are bundled — nothing else to install.

On startup the app makes a single anonymous request to GitHub to check for a
new release and shows an "Update available" button if there is one. Nothing is
ever sent anywhere.

## Build from source

Requires [uv](https://docs.astral.sh/uv/), plus `ffmpeg` and `wkhtmltopdf`
available on `PATH`.

```bash
uv sync
uv run python -m pytest                    # run tests
uv run python -m flagship_converter.app    # run from source
uv run python build.py                     # build dist/FlagshipConverter
```

Releases are built with `uv run python release.py` (needs Inno Setup 6 and an
authenticated gh CLI).

## License

[MIT](LICENSE)
````

- [ ] **Step 3: Проверить, что приложение запускается из исходников**

Run: `uv run python -c "from flagship_converter.app import main; print('import ok')"`
Expected: `import ok`

- [ ] **Step 4: Commit**

```bash
git add README.md docs/assets/screenshot.png
git commit -m "docs: add readme with download and build instructions"
```

---

### Task 6: Инструменты, пуш и публикация v1.0.0 (вместе с пользователем)

Этот таск — единственный с внешними эффектами (пуш, публичный релиз, установка
софта). Каждый внешний шаг — только после явного «да» пользователя.

**Files:** нет новых; используется всё из Tasks 1–5.

**Interfaces:**
- Consumes: `release.py` (Task 4), README (Task 5).
- Produces: опубликованный релиз `v1.0.0` c тремя артефактами; заполненная шапка About на GitHub.

- [ ] **Step 1: Установить инструменты (спросить пользователя)**

```powershell
winget install JRSoftware.InnoSetup
winget install GitHub.cli
```

Затем **пользователь сам** выполняет интерактивную авторизацию:

```powershell
gh auth login
```

(выбрать GitHub.com → HTTPS → Login with a web browser)

- [ ] **Step 2: Запушить main (спросить пользователя)**

```bash
git push origin main
```

Expected: без ошибок; README и LICENSE видны на github.com/PASII11/flagship_converter.

- [ ] **Step 3: Dry-run релиза**

```bash
uv run python release.py --dry-run
```

Expected: `Версия 1.0.0: все проверки пройдены` и `dry-run: сборка и публикация пропущены`. Если ошибка — чинить по сообщению (грязное дерево / нет ISCC / нет gh).

- [ ] **Step 4: Полный релиз (спросить пользователя; долгий шаг)**

```bash
uv run python release.py
```

Ожидание: сборка PyInstaller (10–30 мин) → ZIP (минуты) → ISCC-компиляция
(10–20 мин, LZMA на 1.3 ГБ) → заливка ~1.4 ГБ артефактов на GitHub (зависит от
канала). Expected в конце: `Релиз v1.0.0 опубликован`.

- [ ] **Step 5: Заполнить шапку About**

```bash
gh repo edit PASII11/flagship_converter --description "Privacy-first local file converter for Windows: images, video, audio, documents with OCR" --add-topic file-converter --add-topic ffmpeg --add-topic pyside6 --add-topic windows --add-topic offline --add-topic ocr
```

- [ ] **Step 6: Проверить релиз глазами пользователя**

- Открыть https://github.com/PASII11/flagship_converter/releases/latest — три файла на месте (Setup, ZIP, SHA256SUMS).
- Скачать Setup.exe, установить, запустить — приложение работает.
- Проверка кнопки обновления: временно поставить в `version.py` `0.9.0`, запустить из исходников `uv run python -m flagship_converter.app` — в топ-баре появляется «Доступно обновление v1.0.0», клик открывает страницу релиза. Вернуть `1.0.0`.
