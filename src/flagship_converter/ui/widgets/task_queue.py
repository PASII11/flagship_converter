"""Очередь строк FileRow с empty state и bulk-операциями."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from flagship_converter.ui import theme
from flagship_converter.ui.presets import Preset
from flagship_converter.ui.widgets.file_row import FileRow


class TaskQueue(QWidget):
    files_changed = Signal(int)
    add_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: dict[str, FileRow] = {}
        self.default_video_codec: str | None = None

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        container = QWidget()
        outer_col = QVBoxLayout(container)
        outer_col.setContentsMargins(0, 0, 6, 0)
        outer_col.setSpacing(theme.SPACING["md"])

        self._empty = self._build_empty_state()
        outer_col.addWidget(self._empty)

        self._panel = QFrame()
        self._panel.setObjectName("QueuePanel")
        self._panel_col = QVBoxLayout(self._panel)
        self._panel_col.setContentsMargins(0, 0, 0, 0)
        self._panel_col.setSpacing(0)
        self._panel.setVisible(False)
        outer_col.addWidget(self._panel)
        outer_col.addStretch()

        self._scroll.setWidget(container)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._scroll)
        self.apply_theme()

    def _build_empty_state(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("EmptyState")
        frame.setMinimumHeight(220)
        col = QVBoxLayout(frame)
        col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.setSpacing(theme.SPACING["sm"])
        self._empty_title = QLabel("Перетащите файлы сюда")
        self._empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_sub = QLabel("или нажмите кнопку, чтобы выбрать вручную")
        self._empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_btn = QPushButton("Выбрать файлы")
        self._empty_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._empty_btn.setFixedHeight(34)
        self._empty_btn.clicked.connect(self.add_clicked.emit)
        col.addWidget(self._empty_title)
        col.addWidget(self._empty_sub)
        col.addSpacing(theme.SPACING["sm"])
        col.addWidget(self._empty_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        return frame

    # -- данные --

    def add_files(self, paths: list[str | Path]) -> int:
        existing = {r.file_path.resolve() for r in self._rows.values()}
        added = 0
        for raw in paths:
            p = Path(raw).resolve()
            if p in existing or not p.is_file():
                continue
            row = FileRow(p, default_video_codec=self.default_video_codec)
            row.remove_requested.connect(self._on_remove)
            self._panel_col.addWidget(row)
            self._rows[row.card_id] = row
            existing.add(p)
            added += 1
        if added:
            self._sync_visibility()
            self.files_changed.emit(len(self._rows))
        return added

    def clear_all(self) -> None:
        for row in list(self._rows.values()):
            row.setParent(None)
            row.deleteLater()
        self._rows.clear()
        self._sync_visibility()
        self.files_changed.emit(0)

    def rows(self) -> list[FileRow]:
        return list(self._rows.values())

    def get_row(self, card_id: str) -> FileRow | None:
        return self._rows.get(card_id)

    def bulk_set_format(self, category: str, ext: str) -> int:
        changed = 0
        for row in self._rows.values():
            if row.category != category or row.is_overridden:
                continue
            row.set_target_format(ext)
            changed += 1
        return changed

    def apply_preset(self, preset: Preset) -> None:
        for row in self._rows.values():
            if not row.is_overridden:
                row.apply_preset(preset)

    def categories_present(self) -> set[str]:
        return {r.category for r in self._rows.values() if r.is_convertible()}

    def lock_all(self, locked: bool) -> None:
        for row in self._rows.values():
            row.lock_controls(locked)

    def count(self) -> int:
        return len(self._rows)

    def convertible_count(self) -> int:
        return sum(1 for r in self._rows.values() if r.is_convertible())

    def has_convertible_files(self) -> bool:
        return self.convertible_count() > 0

    # -- вид --

    def apply_theme(self, p: theme.Palette | None = None) -> None:
        p = p or theme.palette()
        self._scroll.setStyleSheet(theme.scroll_area_qss(p))
        self._panel.setStyleSheet(
            "QFrame#QueuePanel {"
            f"background-color: {p.surface};"
            f"border: 1px solid {p.border};"
            f"border-radius: {theme.RADIUS['panel']}px;"
            "}"
        )
        self._empty.setStyleSheet(
            "QFrame#EmptyState {"
            f"background-color: {p.surface};"
            f"border: 2px dashed {p.border_strong};"
            f"border-radius: {theme.RADIUS['panel']}px;"
            "}"
        )
        self._empty_title.setStyleSheet(theme.text_style(p.text_primary, 15, 600))
        self._empty_sub.setStyleSheet(theme.text_style(p.text_secondary, 13, 400))
        self._empty_btn.setStyleSheet(theme.secondary_button_qss(p))
        for row in self._rows.values():
            row.apply_theme(p)

    def _sync_visibility(self) -> None:
        has_rows = bool(self._rows)
        self._empty.setVisible(not has_rows)
        self._panel.setVisible(has_rows)

    def _on_remove(self, card_id: str) -> None:
        row = self._rows.pop(card_id, None)
        if row:
            row.setParent(None)
            row.deleteLater()
        self._sync_visibility()
        self.files_changed.emit(len(self._rows))
