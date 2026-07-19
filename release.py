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
    on_remote = subprocess.run(
        ["git", "branch", "-r", "--contains", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if not on_remote:
        raise ReleaseError("HEAD не запушен на origin — выполните git push")
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
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    # Тег создаёт сам gh вместе с релизом: при ошибке не остаётся
    # полуопубликованного состояния, повторный запуск безопасен.
    run([
        "gh", "release", "create", tag,
        *artifacts,
        "--target", head,
        "--title", f"Flagship Converter {version}",
        "--notes", notes,
    ])
    run(["git", "fetch", "--tags", "origin"])


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
