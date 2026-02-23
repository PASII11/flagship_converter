"""Скрипт сборки приложения в .exe файл."""

import os
import shutil
import subprocess
from pathlib import Path

def main():
    FFMPEG_PATH = Path(shutil.which("ffmpeg") or "")
    WKHTML_PATH = Path(r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")

    if not FFMPEG_PATH.exists():
        raise FileNotFoundError("FFmpeg не найден в системе. Добавьте его в PATH.")
    if not WKHTML_PATH.exists():
        raise FileNotFoundError(f"wkhtmltopdf не найден по пути: {WKHTML_PATH}")

    print("✅ Бинарники найдены.")

    build_dir = Path("build_tools")
    build_dir.mkdir(exist_ok=True)

    shutil.copy2(FFMPEG_PATH, build_dir / "ffmpeg.exe")
    shutil.copy2(WKHTML_PATH, build_dir / "wkhtmltopdf.exe")

    print("⚙️ Запускаем PyInstaller...")

    cmd = [
        "uv", "run", "pyinstaller",
        "--noconfirm",
        "--name=FlagshipConverter",
        "--windowed", # Отключаем консоль, это решает баг с Drag&Drop (UAC)
        "--add-binary=build_tools/ffmpeg.exe;.",
        "--add-binary=build_tools/wkhtmltopdf.exe;.",
        # Собираем все скрытые файлы, DLL и папки с ресурсами
        "--collect-all=docling",
        "--collect-all=docling_parse",
        "--collect-all=docling_core",
        "--collect-all=huggingface_hub",
        "--collect-all=pypdfium2",
        "--collect-all=torch",
        "--collect-all=spacy",
        "--collect-all=transformers",
        "--collect-all=pydantic",
        "--hidden-import=pytorch",
        # Копируем текстовые метаданные (версии)
        "--copy-metadata=docling",
        "--copy-metadata=docling-core",
        "--copy-metadata=docling-ibm-models",
        "--copy-metadata=docling-parse",
        "--copy-metadata=pypdfium2",
        "--copy-metadata=torch",
        "--copy-metadata=torchvision",
        "src/flagship_converter/app.py"
    ]

    subprocess.run(cmd, check=True)

    print("🚀 Сборка завершена! Ищите .exe в папке dist/FlagshipConverter")

if __name__ == "__main__":
    main()
