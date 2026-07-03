"""Командная строка страницы конвертера."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton,
)

from flagship_converter.ui import theme
from flagship_converter.ui.presets import Preset


class CommandBar(QFrame):
    add_files_clicked = Signal()
    preset_selected = Signal(str)
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

        self._preset_label = QLabel("Пресет")
        self._preset_box = QComboBox()
        self._preset_box.setMinimumWidth(180)
        self._preset_box.currentIndexChanged.connect(self._on_preset_index)

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
        row.addWidget(self._preset_label)
        row.addWidget(self._preset_box)
        row.addWidget(self._folder_btn)
        row.addStretch()
        row.addWidget(self._convert_btn)
        row.addWidget(self._cancel_btn)
        self.apply_theme()

    def _on_preset_index(self, _index: int) -> None:
        self.preset_selected.emit(self.current_preset_id())

    def set_presets(self, presets: list[Preset], current_id: str = "") -> None:
        self._preset_box.blockSignals(True)
        self._preset_box.clear()
        self._preset_box.addItem("Свои настройки", "")
        for preset in presets:
            self._preset_box.addItem(preset.name, preset.id)
        index = max(0, self._preset_box.findData(current_id))
        self._preset_box.setCurrentIndex(index)
        self._preset_box.blockSignals(False)

    def current_preset_id(self) -> str:
        return str(self._preset_box.currentData() or "")

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
        for w in (self._add_btn, self._preset_box, self._folder_btn):
            w.setEnabled(not converting)

    def apply_theme(self, p: theme.Palette | None = None) -> None:
        p = p or theme.palette()
        self.setStyleSheet(theme.panel_qss("CommandBar", p))
        self._add_btn.setStyleSheet(theme.secondary_button_qss(p))
        self._preset_label.setStyleSheet(theme.text_style(p.text_secondary, 12, 400))
        self._preset_box.setStyleSheet(theme.input_qss(p))
        self._folder_btn.setStyleSheet(theme.ghost_button_qss(p))
        self._convert_btn.setStyleSheet(theme.primary_button_qss(p))
        self._cancel_btn.setStyleSheet(theme.ghost_button_qss(p, danger=True))
