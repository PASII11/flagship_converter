"""Прокручиваемая очередь карточек файлов."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from flagship_converter.ui.widgets.file_card import FileCard


class TaskQueue(QWidget):
    """Вертикальный список FileCard с прокруткой. Поддерживает append-режим."""

    files_changed = Signal(int)  # количество карточек после изменения

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cards: dict[str, FileCard] = {}  # card_id → FileCard

        # Прокручиваемая область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # Внутренний контейнер
        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._inner = QVBoxLayout(self._container)
        self._inner.setContentsMargins(0, 0, 4, 0)
        self._inner.setSpacing(6)
        self._inner.addStretch()   # стрейч в конце — карточки прижаты к верху

        scroll.setWidget(self._container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_files(self, paths: list[str | Path]) -> None:
        """Добавить файлы. Дубликаты по абсолютному пути пропускаются."""
        existing_paths = {c.file_path.resolve() for c in self._cards.values()}
        added = 0
        for raw in paths:
            p = Path(raw).resolve()
            if p in existing_paths or not p.is_file():
                continue
            card = FileCard(p)
            card.remove_requested.connect(self._on_remove_requested)
            # Вставляем перед последним элементом (stretch)
            self._inner.insertWidget(self._inner.count() - 1, card)
            self._cards[card.card_id] = card
            existing_paths.add(p)
            added += 1
        if added:
            self.files_changed.emit(len(self._cards))

    def clear_all(self) -> None:
        for card in list(self._cards.values()):
            card.setParent(None)  # type: ignore[arg-type]
            card.deleteLater()
        self._cards.clear()
        self.files_changed.emit(0)

    def cards(self) -> list[FileCard]:
        """Текущий список карточек в порядке добавления."""
        return list(self._cards.values())

    def get_card(self, card_id: str) -> FileCard | None:
        return self._cards.get(card_id)

    def lock_all(self, locked: bool) -> None:
        for card in self._cards.values():
            card.lock_controls(locked)

    def count(self) -> int:
        return len(self._cards)

    # ------------------------------------------------------------------
    # Внутренние слоты
    # ------------------------------------------------------------------

    def _on_remove_requested(self, card_id: str) -> None:
        card = self._cards.pop(card_id, None)
        if card:
            card.setParent(None)  # type: ignore[arg-type]
            card.deleteLater()
        self.files_changed.emit(len(self._cards))
