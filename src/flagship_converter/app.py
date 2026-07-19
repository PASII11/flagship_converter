"""Точка входа приложения."""
from __future__ import annotations

import multiprocessing
import sys

from PySide6.QtWidgets import QApplication

from flagship_converter.ui.main_window import MainWindow
from flagship_converter.version import __version__


def main() -> None:
    """Запустить приложение."""
    multiprocessing.freeze_support()

    app = QApplication(sys.argv)

    app.setStyle("Fusion")

    app.setApplicationName("Flagship File Converter")
    app.setApplicationVersion(__version__)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
