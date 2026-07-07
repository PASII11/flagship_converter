"""Build the Windows executable with bundled local conversion tools."""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

DATA_SEP = ";" if os.name == "nt" else ":"


def _required_binary(name: str, default_paths: list[Path] | None = None) -> Path:
    found = shutil.which(name)
    if found:
        return Path(found)

    for candidate in default_paths or []:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"Required binary was not found: {name}")


def _package_dir(package: str) -> Path:
    spec = importlib.util.find_spec(package)
    if not spec or not spec.origin:
        raise RuntimeError(f"Required package is not importable: {package}")
    return Path(spec.origin).resolve().parent


def _ensure_docling_models(build_dir: Path) -> Path:
    models_dir = build_dir / "docling_models"
    if models_dir.exists() and any(models_dir.iterdir()):
        return models_dir

    models_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "docling.cli.tools",
            "models",
            "download",
            "--output-dir",
            str(models_dir),
        ],
        check=True,
    )
    return models_dir


def main() -> None:
    build_dir = Path("build_tools")
    build_dir.mkdir(exist_ok=True)

    ffmpeg_path = _required_binary("ffmpeg")
    wkhtml_path = _required_binary(
        "wkhtmltopdf",
        [
            Path(r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"),
            Path(r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe"),
        ],
    )

    shutil.copy2(ffmpeg_path, build_dir / "ffmpeg.exe")
    shutil.copy2(wkhtml_path, build_dir / "wkhtmltopdf.exe")

    rapid_dir = _package_dir("rapidocr")
    docling_models_dir = _ensure_docling_models(build_dir)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--name=FlagshipConverter",
        "--windowed",
        f"--add-binary={build_dir / 'ffmpeg.exe'}{DATA_SEP}.",
        f"--add-binary={build_dir / 'wkhtmltopdf.exe'}{DATA_SEP}.",
        f"--add-data={rapid_dir}{DATA_SEP}rapidocr",
        f"--add-data={docling_models_dir}{DATA_SEP}docling_models",
        "--collect-all=docling",
        "--collect-all=docling_parse",
        "--collect-all=docling_core",
        "--collect-all=huggingface_hub",
        "--collect-all=pypdfium2",
        "--collect-all=pdf2docx",
        "--collect-all=fitz",
        "--collect-all=torch",
        "--collect-all=spacy",
        "--collect-all=transformers",
        "--collect-all=pydantic",
        "--collect-all=onnxruntime",
        "--hidden-import=torch",
        "--hidden-import=rapidocr",
        "--copy-metadata=docling",
        "--copy-metadata=docling-core",
        "--copy-metadata=docling-ibm-models",
        "--copy-metadata=docling-parse",
        "--copy-metadata=pypdfium2",
        "--copy-metadata=pdf2docx",
        "--copy-metadata=torch",
        "--copy-metadata=torchvision",
        "src/flagship_converter/app.py",
    ]

    subprocess.run(cmd, check=True)
    print("Build complete. See dist/FlagshipConverter.")


if __name__ == "__main__":
    main()
