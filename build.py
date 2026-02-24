"""Скрипт сборки приложения в .exe файл."""
import os
import shutil
import subprocess
from pathlib import Path

# Импортируем проблемную библиотеку, чтобы физически найти её файлы
import rapidocr_onnxruntime

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

    # Находим реальный путь до папки rapidocr_onnxruntime
    rapid_dir = os.path.dirname(rapidocr_onnxruntime.__file__)
    print(f"📦 Найден rapidocr_onnxruntime по пути: {rapid_dir}")

    print("⚙️ Запускаем PyInstaller...")

    cmd = [
        "uv", "run", "pyinstaller",
        "--noconfirm",
        "--name=FlagshipConverter",
        "--windowed",
        "--add-binary=build_tools/ffmpeg.exe;.",
        "--add-binary=build_tools/wkhtmltopdf.exe;.",

        # ЖЕЛЕЗОБЕТОННЫЙ ФИКС: Ручное копирование всей папки rapidocr со всеми конфигами и моделями!
        f"--add-data={rapid_dir};rapidocr_onnxruntime",

        # Собираем все скрытые файлы
        "--collect-all=docling",
        "--collect-all=docling_parse",
        "--collect-all=docling_core",
        "--collect-all=huggingface_hub",
        "--collect-all=pypdfium2",
        "--collect-all=torch",
        "--collect-all=spacy",
        "--collect-all=transformers",
        "--collect-all=pydantic",
        "--collect-all=onnxruntime",

        "--hidden-import=pytorch",
        "--hidden-import=rapidocr_onnxruntime",

        # Метаданные
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
