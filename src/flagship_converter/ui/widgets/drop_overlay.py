"""Полноэкранный оверлей при перетаскивании файлов."""
from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget

from flagship_converter.ui import theme


class DropOverlay(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

        col = QVBoxLayout(self)
        col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(self._label)

        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._anim = QPropertyAnimation(self._effect, b"opacity")
        self._anim.setDuration(150)

    def show_overlay(self, text: str = "Отпустите, чтобы добавить файлы") -> None:
        p = theme.palette()
        self._label.setText(text)
        self._label.setStyleSheet(
            f"color: {p.text_primary}; font-size: 20px; font-weight: 700;"
            f"background-color: {p.surface}; border: 2px dashed {p.running};"
            f"border-radius: {theme.RADIUS['panel']}px; padding: 24px 40px;"
        )
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
        self.raise_()
        self.show()
        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def hide_overlay(self) -> None:
        self.hide()

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        p = theme.palette()
        veil = QColor(p.app_bg)
        veil.setAlpha(200)
        painter.fillRect(self.rect(), veil)
