"""Drag-and-drop file intake widget."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QFont, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget

from flagship_converter.ui import theme


class DropZone(QWidget):
    """Drop target that also works as a click-to-select control."""

    files_dropped = Signal(list)  # list[str]
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(168)
        self._hovered = False
        self._pressed = False
        self.setToolTip("Выбрать файлы")

    def apply_theme(self, p: theme.Palette | None = None) -> None:
        self.update()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # type: ignore[override]
        if self.isEnabled() and event.mimeData().hasUrls():
            self._hovered = True
            self.update()
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: object) -> None:  # type: ignore[override]
        self._hovered = False
        self.update()

    def dropEvent(self, event: QDropEvent) -> None:  # type: ignore[override]
        self._hovered = False
        self._pressed = False
        self.update()
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)
        event.acceptProposedAction()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        was_pressed = self._pressed
        self._pressed = False
        self.update()
        if self.isEnabled() and was_pressed and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: object) -> None:  # type: ignore[override]
        key = event.key() if hasattr(event, "key") else None
        if self.isEnabled() and key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
            return
        super().keyPressEvent(event)  # type: ignore[arg-type]

    def paintEvent(self, event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        p = theme.palette()
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        if not self.isEnabled():
            bg_color = QColor(p.surface_secondary)
            border_color = QColor(p.border)
            title_color = QColor(p.text_muted)
            subtitle_color = QColor(p.text_muted)
        elif self._hovered:
            bg_color = QColor(p.accent_soft)
            border_color = QColor(p.accent)
            title_color = QColor(p.accent)
            subtitle_color = QColor(p.text_secondary)
        elif self._pressed:
            bg_color = QColor(p.accent_soft)
            border_color = QColor(p.accent_hover)
            title_color = QColor(p.accent_pressed)
            subtitle_color = QColor(p.text_secondary)
        else:
            bg_color = QColor(p.surface_elevated)
            border_color = QColor(p.border_strong)
            title_color = QColor(p.text_primary)
            subtitle_color = QColor(p.text_secondary)

        painter.setBrush(bg_color)
        pen = QPen(border_color, 2)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 14, 14)

        self._draw_upload_mark(painter, title_color)
        self._draw_text(painter, title_color, subtitle_color)

    def _draw_upload_mark(self, painter: QPainter, color: QColor) -> None:
        center_x = self.width() / 2
        top = max(22, self.height() / 2 - 54)
        pen = QPen(color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        tray = QRectF(center_x - 24, top + 34, 48, 20)
        painter.drawRoundedRect(tray, 7, 7)
        painter.drawLine(QPointF(center_x, top + 10), QPointF(center_x, top + 38))
        painter.drawLine(QPointF(center_x, top + 10), QPointF(center_x - 10, top + 22))
        painter.drawLine(QPointF(center_x, top + 10), QPointF(center_x + 10, top + 22))

    def _draw_text(self, painter: QPainter, title_color: QColor, subtitle_color: QColor) -> None:
        title_font = QFont("Segoe UI")
        title_font.setPointSize(15)
        title_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(title_font)
        painter.setPen(title_color)
        painter.drawText(
            QRectF(0, self.height() / 2 + 10, self.width(), 28),
            Qt.AlignmentFlag.AlignCenter,
            "Перетащите файлы сюда",
        )

        subtitle_font = QFont("Segoe UI")
        subtitle_font.setPointSize(10)
        painter.setFont(subtitle_font)
        painter.setPen(subtitle_color)
        painter.drawText(
            QRectF(0, self.height() / 2 + 38, self.width(), 24),
            Qt.AlignmentFlag.AlignCenter,
            "или нажмите, чтобы выбрать их вручную",
        )
