"""Точка входа приложения."""
from __future__ import annotations

import multiprocessing
import sys

from PySide6.QtWidgets import QApplication

from flagship_converter.ui.main_window import MainWindow


def main() -> None:
    """Запустить приложение."""
    # Обязательно для корректной работы multiprocessing в PyInstaller (Windows)
    multiprocessing.freeze_support()

    app = QApplication(sys.argv)

    # ---------------------------------------------------------
    # ЖЕЛЕЗОБЕТОННЫЙ ФИКС СТИЛЕЙ:
    # Отключаем системный движок отрисовки Windows,
    # который ломает наши кастомные QSS-стили.
    # ---------------------------------------------------------
    app.setStyle("Fusion")

    app.setApplicationName("Flagship File Converter")
    app.setApplicationVersion("1.0.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
