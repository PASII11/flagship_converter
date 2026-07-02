"""Scrollable queue of file conversion cards."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget

from flagship_converter.ui import theme
from flagship_converter.ui.widgets.file_card import FileCard


class TaskQueue(QWidget):
    """Vertical list of FileCard widgets with an empty state."""

    files_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cards: dict[str, FileCard] = {}

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll = scroll
        self._scroll.setStyleSheet(theme.scroll_area_qss())

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._inner = QVBoxLayout(self._container)
        self._inner.setContentsMargins(0, 0, 6, 0)
        self._inner.setSpacing(10)

        self._empty_state = self._build_empty_state()
        self._inner.addWidget(self._empty_state)
        self._inner.addStretch()

        scroll.setWidget(self._container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.apply_theme()

    def _build_empty_state(self) -> QFrame:
        empty = QFrame()
        empty.setObjectName("SubtlePanel")
        empty.setMinimumHeight(170)

        layout = QVBoxLayout(empty)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._empty_title = QLabel("Очередь пуста")
        self._empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._empty_subtitle = QLabel(
            "Добавленные файлы появятся здесь вместе с форматом, прогрессом и результатом."
        )
        self._empty_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_subtitle.setWordWrap(True)

        layout.addWidget(self._empty_title)
        layout.addWidget(self._empty_subtitle)
        return empty

    def apply_theme(self, p: theme.Palette | None = None) -> None:
        p = p or theme.palette()
        self._scroll.setStyleSheet(theme.scroll_area_qss(p))
        self._empty_state.setStyleSheet(theme.panel_qss("SubtlePanel", p, radius=16))
        self._empty_title.setStyleSheet(theme.text_style(p.text_primary, 18, 760))
        self._empty_subtitle.setStyleSheet(theme.text_style(p.text_secondary, 13, 430))
        for card in self._cards.values():
            card.apply_theme(p)

    def add_files(self, paths: list[str | Path]) -> int:
        """Add files and skip duplicate or non-file paths. Returns added count."""
        existing_paths = {c.file_path.resolve() for c in self._cards.values()}
        added = 0
        for raw in paths:
            p = Path(raw).resolve()
            if p in existing_paths or not p.is_file():
                continue
            card = FileCard(p)
            card.apply_theme()
            card.remove_requested.connect(self._on_remove_requested)
            self._inner.insertWidget(self._inner.count() - 1, card)
            self._cards[card.card_id] = card
            existing_paths.add(p)
            added += 1
        if added:
            self._sync_empty_state()
            self.files_changed.emit(len(self._cards))
        return added

    def clear_all(self) -> None:
        for card in list(self._cards.values()):
            card.setParent(None)  # type: ignore[arg-type]
            card.deleteLater()
        self._cards.clear()
        self._sync_empty_state()
        self.files_changed.emit(0)

    def cards(self) -> list[FileCard]:
        """Current cards in insertion order."""
        return list(self._cards.values())

    def get_card(self, card_id: str) -> FileCard | None:
        return self._cards.get(card_id)

    def lock_all(self, locked: bool) -> None:
        for card in self._cards.values():
            card.lock_controls(locked)

    def count(self) -> int:
        return len(self._cards)

    def convertible_count(self) -> int:
        return sum(1 for card in self._cards.values() if card.is_convertible())

    def has_convertible_files(self) -> bool:
        return self.convertible_count() > 0

    def _sync_empty_state(self) -> None:
        self._empty_state.setVisible(not self._cards)

    def _on_remove_requested(self, card_id: str) -> None:
        card = self._cards.pop(card_id, None)
        if card:
            card.setParent(None)  # type: ignore[arg-type]
            card.deleteLater()
        self._sync_empty_state()
        self.files_changed.emit(len(self._cards))
