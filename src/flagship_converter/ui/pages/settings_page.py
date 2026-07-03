"""Страница настроек приложения."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QVBoxLayout, QWidget,
)

from flagship_converter.ui import theme
from flagship_converter.ui.settings import AppSettings


class SettingsPage(QWidget):
    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self._settings = settings
        self._build_ui()
        self._load_from_settings()
        self.apply_theme()

    def _row(self, label_text: str, widget: QWidget) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(theme.SPACING["md"])
        label = QLabel(label_text)
        label.setObjectName("SettingLabel")
        label.setMinimumWidth(240)
        h.addWidget(label)
        h.addWidget(widget)
        h.addStretch()
        return row

    def _build_ui(self) -> None:
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(theme.SPACING["lg"])

        self._title = QLabel("Настройки")
        col.addWidget(self._title)

        self._panel = QFrame()
        self._panel.setObjectName("SettingsPanel")
        panel_col = QVBoxLayout(self._panel)
        panel_col.setContentsMargins(
            theme.SPACING["lg"], theme.SPACING["lg"],
            theme.SPACING["lg"], theme.SPACING["lg"],
        )
        panel_col.setSpacing(theme.SPACING["lg"])

        self._output_mode_box = QComboBox()
        self._output_mode_box.addItem("converted/ рядом с исходником", "beside")
        self._output_mode_box.addItem("Фиксированная папка", "fixed")
        self._output_mode_box.currentIndexChanged.connect(self._on_output_mode)
        panel_col.addWidget(self._row("Папка вывода", self._output_mode_box))

        self._folder_btn = QPushButton("Выбрать папку…")
        self._folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._folder_btn.clicked.connect(self._pick_folder)
        panel_col.addWidget(self._row("Фиксированная папка", self._folder_btn))

        self._conflict_box = QComboBox()
        self._conflict_box.addItem("Добавлять суффикс (1)", False)
        self._conflict_box.addItem("Перезаписывать", True)
        self._conflict_box.currentIndexChanged.connect(
            lambda _i: setattr(
                self._settings, "overwrite",
                bool(self._conflict_box.currentData()),
            )
        )
        panel_col.addWidget(self._row("Конфликты имён", self._conflict_box))

        self._theme_box = QComboBox()
        self._theme_box.addItem("Система", "system")
        self._theme_box.addItem("Светлая", "light")
        self._theme_box.addItem("Тёмная", "dark")
        self._theme_box.currentIndexChanged.connect(
            lambda _i: setattr(
                self._settings, "theme_mode",
                str(self._theme_box.currentData()),
            )
        )
        panel_col.addWidget(self._row("Тема", self._theme_box))

        self._workers_spin = QSpinBox()
        self._workers_spin.setRange(0, 16)
        self._workers_spin.setSpecialValueText("Авто")
        self._workers_spin.valueChanged.connect(
            lambda v: setattr(self._settings, "max_workers", int(v))
        )
        panel_col.addWidget(
            self._row("Максимум параллельных задач", self._workers_spin)
        )

        self._codec_box = QComboBox()
        self._codec_box.addItems(
            ["Авто (CPU x264)", "AMD (AMF)", "NVIDIA (NVENC)", "Intel (QSV)"]
        )
        self._codec_box.currentTextChanged.connect(
            lambda text: setattr(self._settings, "default_video_codec", text)
        )
        panel_col.addWidget(
            self._row("Кодек видео по умолчанию", self._codec_box)
        )

        col.addWidget(self._panel)
        col.addStretch()

    def _load_from_settings(self) -> None:
        s = self._settings
        boxes = (
            (self._output_mode_box, s.output_mode),
            (self._theme_box, s.theme_mode),
        )
        for box, value in boxes:
            box.blockSignals(True)
            box.setCurrentIndex(max(0, box.findData(value)))
            box.blockSignals(False)
        self._conflict_box.blockSignals(True)
        self._conflict_box.setCurrentIndex(1 if s.overwrite else 0)
        self._conflict_box.blockSignals(False)
        self._workers_spin.blockSignals(True)
        self._workers_spin.setValue(s.max_workers)
        self._workers_spin.blockSignals(False)
        self._codec_box.blockSignals(True)
        self._codec_box.setCurrentText(s.default_video_codec)
        self._codec_box.blockSignals(False)
        if s.fixed_output_dir:
            self._folder_btn.setText(s.fixed_output_dir)

    def _on_output_mode(self, _index: int) -> None:
        self._settings.output_mode = str(self._output_mode_box.currentData())

    def _pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку для сохранения"
        )
        if folder:
            self._settings.fixed_output_dir = folder
            self._folder_btn.setText(folder)

    def apply_theme(self, p: theme.Palette | None = None) -> None:
        p = p or theme.palette()
        self._title.setStyleSheet(theme.text_style(p.text_primary, 20, 700))
        self._panel.setStyleSheet(theme.panel_qss("SettingsPanel", p))
        for label in self._panel.findChildren(QLabel, "SettingLabel"):
            label.setStyleSheet(theme.text_style(p.text_secondary, 13, 400))
        for box in (
            self._output_mode_box, self._conflict_box,
            self._theme_box, self._codec_box,
        ):
            box.setStyleSheet(theme.input_qss(p))
        self._workers_spin.setStyleSheet(theme.input_qss(p))
        self._folder_btn.setStyleSheet(theme.secondary_button_qss(p))
