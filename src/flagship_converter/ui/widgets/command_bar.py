"""Командная строка страницы конвертера."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton

from flagship_converter.ui import theme


class CommandBar(QFrame):
    add_files_clicked = Signal()
    folder_clicked = Signal()
    convert_clicked = Signal()
    cancel_clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("CommandBar")
        row = QHBoxLayout(self)
        row.setContentsMargins(
            theme.SPACING["lg"], theme.SPACING["md"],
            theme.SPACING["lg"], theme.SPACING["md"],
        )
        row.setSpacing(theme.SPACING["md"])

        self._add_btn = QPushButton("Добавить файлы")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self.add_files_clicked.emit)

        self._folder_btn = QPushButton("converted/ рядом с исходником")
        self._folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._folder_btn.clicked.connect(self.folder_clicked.emit)

        self._convert_btn = QPushButton("Конвертировать")
        self._convert_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._convert_btn.setFixedHeight(40)
        self._convert_btn.setEnabled(False)
        self._convert_btn.clicked.connect(self.convert_clicked.emit)

        self._cancel_btn = QPushButton("Отменить")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setFixedHeight(40)
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self.cancel_clicked.emit)

        row.addWidget(self._add_btn)
        row.addWidget(self._folder_btn)
        row.addStretch()
        row.addWidget(self._convert_btn)
        row.addWidget(self._cancel_btn)
        self.apply_theme()

    def set_folder_text(self, text: str) -> None:
        self._folder_btn.setText(text)
        self._folder_btn.setToolTip(text)

    def set_convert_count(self, n: int) -> None:
        self._convert_btn.setText(
            f"Конвертировать {n}" if n > 1 else "Конвертировать"
        )

    def set_convert_enabled(self, enabled: bool) -> None:
        self._convert_btn.setEnabled(enabled)

    def set_converting(self, converting: bool) -> None:
        self._convert_btn.setVisible(not converting)
        self._cancel_btn.setVisible(converting)
        for w in (self._add_btn, self._folder_btn):
            w.setEnabled(not converting)

    def apply_theme(self, p: theme.Palette | None = None) -> None:
        p = p or theme.palette()
        self.setStyleSheet(theme.panel_qss("CommandBar", p))
        self._add_btn.setStyleSheet(theme.secondary_button_qss(p))
        self._folder_btn.setStyleSheet(theme.ghost_button_qss(p))
        self._convert_btn.setStyleSheet(theme.primary_button_qss(p))
        self._cancel_btn.setStyleSheet(theme.ghost_button_qss(p, danger=True))
