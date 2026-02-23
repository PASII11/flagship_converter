"""Виджет элемента задачи конвертации с прогресс-баром."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget


class JobItemWidget(QWidget):
    """Отображает статус файла с полосой прогресса."""

    def __init__(self, filename: str, target: str) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)

        top_layout = QHBoxLayout()
        self._name_label = QLabel(f"📄 {filename}  →  {target.upper()}")
        font = self._name_label.font()
        font.setBold(True)
        self._name_label.setFont(font)

        self._status_label = QLabel("Ожидание")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        top_layout.addWidget(self._name_label)
        top_layout.addWidget(self._status_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(6)

        # Стилизация под современный UI
        self._progress_bar.setStyleSheet(
            "QProgressBar { border: none; background-color: #2A2D3E; border-radius: 3px; } "
            "QProgressBar::chunk { background-color: #7C83FD; border-radius: 3px; }"
        )

        self._layout.addLayout(top_layout)
        self._layout.addWidget(self._progress_bar)

    def set_status(self, text: str, color: str = "") -> None:
        self._status_label.setText(text)
        if color:
            self._status_label.setStyleSheet(f"color: {color};")
        else:
            self._status_label.setStyleSheet("")

    def set_progress(self, percent: int) -> None:
        self._progress_bar.setValue(percent)
