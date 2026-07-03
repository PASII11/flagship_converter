"""Главное окно: топ-бар с навигацией и стек страниц."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from flagship_converter.core.engine import ConversionEngine
from flagship_converter.ui import theme
from flagship_converter.ui.pages.converter_page import ConverterPage
from flagship_converter.ui.pages.presets_page import PresetsPage
from flagship_converter.ui.pages.settings_page import SettingsPage
from flagship_converter.ui.presets import PresetStore
from flagship_converter.ui.settings import AppSettings
from flagship_converter.ui.widgets.drop_overlay import DropOverlay

_THEME_CYCLE = {"system": "light", "light": "dark", "dark": "system"}
_THEME_TITLES = {
    "system": "Тема: Системная",
    "light": "Тема: Светлая",
    "dark": "Тема: Тёмная",
}


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: AppSettings | None = None,
        store: PresetStore | None = None,
        engine: ConversionEngine | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Flagship File Converter")
        self.setMinimumSize(1080, 720)
        self.setAcceptDrops(True)

        self._settings = settings or AppSettings()
        self._store = store or PresetStore()
        self._engine = engine or ConversionEngine(max_workers=self._settings.max_workers or None)
        theme.set_theme_mode(self._settings.theme_mode)

        self._build_ui()
        self._overlay = DropOverlay(self)
        self._settings.changed.connect(self._on_settings_changed)
        self._connect_system_theme_listener()
        self._apply_theme()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        col = QVBoxLayout(root)
        col.setContentsMargins(
            theme.SPACING["xl"], theme.SPACING["lg"],
            theme.SPACING["xl"], theme.SPACING["lg"],
        )
        col.setSpacing(theme.SPACING["lg"])

        top = QWidget()
        top.setFixedHeight(52)
        bar = QHBoxLayout(top)
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(theme.SPACING["md"])

        self._brand_mark = QLabel("F")
        self._brand_mark.setFixedSize(24, 24)
        self._brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._brand_title = QLabel("Flagship")
        bar.addWidget(self._brand_mark)
        bar.addWidget(self._brand_title)
        bar.addStretch()

        self._nav_buttons: list[QPushButton] = []
        for index, title in enumerate(("Конвертер", "Пресеты", "Настройки")):
            btn = QPushButton(title)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(34)
            btn.clicked.connect(lambda _=False, i=index: self._go(i))
            self._nav_buttons.append(btn)
            bar.addWidget(btn)
        bar.addStretch()

        self._theme_btn = QPushButton()
        self._theme_btn.setFixedHeight(34)
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_btn.setToolTip("Переключить тему")
        self._theme_btn.clicked.connect(self._cycle_theme)
        bar.addWidget(self._theme_btn)
        col.addWidget(top)

        self._converter = ConverterPage(self._engine, self._settings, self._store)
        self._presets_page = PresetsPage(self._store)
        self._settings_page = SettingsPage(self._settings)
        self._presets_page.apply_requested.connect(self._apply_preset_and_go)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._converter)
        self._stack.addWidget(self._presets_page)
        self._stack.addWidget(self._settings_page)
        col.addWidget(self._stack, stretch=1)


    def _go(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        self._style_nav()

    def _cycle_theme(self) -> None:
        self._settings.theme_mode = _THEME_CYCLE.get(
            self._settings.theme_mode, "system"
        )

    def _apply_preset_and_go(self, preset_id: str) -> None:
        self._converter.apply_preset_by_id(preset_id)
        self._converter._command_bar.set_presets(
            self._store.presets(), preset_id
        )
        self._go(0)

    def _on_settings_changed(self) -> None:
        theme.set_theme_mode(self._settings.theme_mode)
        self._apply_theme()
        self._engine.set_max_workers(self._settings.max_workers or None)

    def _connect_system_theme_listener(self) -> None:
        qapp = QApplication.instance()
        if qapp is None:
            return
        signal = getattr(qapp.styleHints(), "colorSchemeChanged", None)
        if signal is not None:
            signal.connect(lambda _s: self._apply_theme_if_system())

    def _apply_theme_if_system(self) -> None:
        if theme.theme_mode() == theme.ThemeMode.SYSTEM:
            self._apply_theme()

    def _apply_theme(self) -> None:
        p = theme.palette()
        self.setStyleSheet(theme.app_qss(p))
        self.centralWidget().setStyleSheet(theme.root_qss(p))
        self._brand_mark.setStyleSheet(
            f"color: #FFFFFF; background-color: {p.accent};"
            "border-radius: 6px; font-size: 13px; font-weight: 700;"
        )
        self._brand_title.setStyleSheet(theme.text_style(p.text_primary, 13, 600))
        self._theme_btn.setText(
            _THEME_TITLES.get(self._settings.theme_mode, "Тема")
        )
        self._theme_btn.setStyleSheet(theme.secondary_button_qss(p))
        self._style_nav()
        self._converter.apply_theme(p)
        self._presets_page.apply_theme(p)
        self._settings_page.apply_theme(p)

    def _style_nav(self) -> None:
        p = theme.palette()
        current = self._stack.currentIndex()
        for index, btn in enumerate(self._nav_buttons):
            btn.setStyleSheet(theme.nav_button_qss(index == current, p))


    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            text = (
                "Дождитесь завершения текущей конвертации"
                if self._converter.is_converting
                else "Отпустите, чтобы добавить файлы"
            )
            self._overlay.show_overlay(text)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: object) -> None:
        self._overlay.hide_overlay()

    def dropEvent(self, event: QDropEvent) -> None:
        self._overlay.hide_overlay()
        if self._converter.is_converting:
            event.ignore()
            return
        paths = [
            url.toLocalFile()
            for url in event.mimeData().urls()
            if url.isLocalFile()
        ]
        if paths:
            self._converter.add_files(paths)
            self._go(0)
        event.acceptProposedAction()

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        if self._overlay.isVisible():
            self._overlay.setGeometry(self.rect())
