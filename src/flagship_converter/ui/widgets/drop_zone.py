"""Виджет drag-and-drop зоны для приёма файлов."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QFont, QPainter
from PySide6.QtWidgets import QWidget


class DropZone(QWidget):
    """Центральная зона перетаскивания файлов."""

    files_dropped = Signal(list)  # list[str]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(160)
        self._hovered = False

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            self._hovered = True
            self.update()
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: object) -> None:
        self._hovered = False
        self.update()

    def dropEvent(self, event: QDropEvent) -> None:  # type: ignore[override]
        self._hovered = False
        self.update()
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)
        event.acceptProposedAction()

    def paintEvent(self, event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg_color = QColor("#2A2D3E") if self._hovered else QColor("#1E2030")
        border_color = QColor("#7C83FD") if self._hovered else QColor("#444860")

        painter.setBrush(bg_color)
        pen = painter.pen()
        pen.setColor(border_color)
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawRoundedRect(self.rect().adjusted(4, 4, -4, -4), 12, 12)

        font = QFont()
        font.setPointSize(14)
        painter.setFont(font)
        painter.setPen(QColor("#8B92B8"))
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            "⬇  Перетащите файлы сюда",
        )
