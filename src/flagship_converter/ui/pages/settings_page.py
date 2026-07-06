"""Страница настроек приложения."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from flagship_converter.i18n import t
from flagship_converter.ui import theme
from flagship_converter.ui.settings import AppSettings
from flagship_converter.ui.video_codecs import VIDEO_CODEC_IDS, VIDEO_CODEC_LABELS


class SettingsPage(QWidget):
    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self._settings = settings
        self._build_ui()
        self._load_from_settings()
        settings.changed.connect(self._load_from_settings)
        self.apply_theme()

    def _row(self, label_text: str, widget: QWidget) -> tuple[QWidget, QLabel]:
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
        return row, label

    def _build_ui(self) -> None:
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(theme.SPACING["lg"])

        self._title = QLabel(t("Настройки"))
        col.addWidget(self._title)

        self._panel = QFrame()
        self._panel.setObjectName("SettingsPanel")
        panel_col = QVBoxLayout(self._panel)
        panel_col.setContentsMargins(
            theme.SPACING["lg"], theme.SPACING["lg"],
            theme.SPACING["lg"], theme.SPACING["lg"],
        )
        panel_col.setSpacing(theme.SPACING["lg"])

        self._language_box = QComboBox()
        self._language_box.addItem("Русский", "ru")
        self._language_box.addItem("English", "en")
        self._language_box.currentIndexChanged.connect(
            lambda _i: setattr(
                self._settings, "language",
                str(self._language_box.currentData()),
            )
        )
        row, self._language_label = self._row(t("Язык"), self._language_box)
        panel_col.addWidget(row)

        self._output_mode_box = QComboBox()
        self._output_mode_box.addItem(t("converted/ рядом с исходником"), "beside")
        self._output_mode_box.addItem(t("Фиксированная папка"), "fixed")
        self._output_mode_box.currentIndexChanged.connect(self._on_output_mode)
        row, self._output_mode_label = self._row(t("Папка вывода"), self._output_mode_box)
        panel_col.addWidget(row)

        self._folder_btn = QPushButton(t("Выбрать папку…"))
        self._folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._folder_btn.clicked.connect(self._pick_folder)
        row, self._folder_label = self._row(t("Фиксированная папка"), self._folder_btn)
        panel_col.addWidget(row)

        self._conflict_box = QComboBox()
        self._conflict_box.addItem(t("Добавлять суффикс (1)"), False)
        self._conflict_box.addItem(t("Перезаписывать"), True)
        self._conflict_box.currentIndexChanged.connect(
            lambda _i: setattr(
                self._settings, "overwrite",
                bool(self._conflict_box.currentData()),
            )
        )
        row, self._conflict_label = self._row(t("Конфликты имён"), self._conflict_box)
        panel_col.addWidget(row)

        self._theme_box = QComboBox()
        self._theme_box.addItem(t("Система"), "system")
        self._theme_box.addItem(t("Светлая"), "light")
        self._theme_box.addItem(t("Тёмная"), "dark")
        self._theme_box.currentIndexChanged.connect(
            lambda _i: setattr(
                self._settings, "theme_mode",
                str(self._theme_box.currentData()),
            )
        )
        row, self._theme_label = self._row(t("Тема"), self._theme_box)
        panel_col.addWidget(row)

        self._workers_box = QComboBox()
        self._workers_box.addItem(t("Авто"), 0)
        for count in range(1, 17):
            self._workers_box.addItem(str(count), count)
        self._workers_box.currentIndexChanged.connect(
            lambda _i: setattr(
                self._settings, "max_workers",
                int(self._workers_box.currentData()),
            )
        )
        row, self._workers_label = self._row(
            t("Максимум параллельных задач"), self._workers_box
        )
        panel_col.addWidget(row)

        self._codec_box = QComboBox()
        for codec_id in VIDEO_CODEC_IDS:
            self._codec_box.addItem(t(VIDEO_CODEC_LABELS[codec_id]), codec_id)
        self._codec_box.currentIndexChanged.connect(
            lambda _i: setattr(
                self._settings, "default_video_codec",
                str(self._codec_box.currentData()),
            )
        )
        row, self._codec_label = self._row(
            t("Кодек видео по умолчанию"), self._codec_box
        )
        panel_col.addWidget(row)

        col.addWidget(self._panel)
        col.addStretch()

    def _load_from_settings(self) -> None:
        s = self._settings
        boxes = (
            (self._output_mode_box, s.output_mode),
            (self._theme_box, s.theme_mode),
            (self._language_box, s.language),
        )
        for box, value in boxes:
            box.blockSignals(True)
            box.setCurrentIndex(max(0, box.findData(value)))
            box.blockSignals(False)
        self._conflict_box.blockSignals(True)
        self._conflict_box.setCurrentIndex(1 if s.overwrite else 0)
        self._conflict_box.blockSignals(False)
        self._workers_box.blockSignals(True)
        self._workers_box.setCurrentIndex(
            max(0, self._workers_box.findData(s.max_workers))
        )
        self._workers_box.blockSignals(False)
        self._codec_box.blockSignals(True)
        self._codec_box.setCurrentIndex(
            max(0, self._codec_box.findData(s.default_video_codec))
        )
        self._codec_box.blockSignals(False)
        if s.fixed_output_dir:
            self._folder_btn.setText(s.fixed_output_dir)

    def _on_output_mode(self, _index: int) -> None:
        self._settings.output_mode = str(self._output_mode_box.currentData())

    def _pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, t("Выберите папку для сохранения")
        )
        if folder:
            self._settings.fixed_output_dir = folder
            self._folder_btn.setText(folder)

    def retranslate(self) -> None:
        self._title.setText(t("Настройки"))
        self._language_label.setText(t("Язык"))
        self._output_mode_label.setText(t("Папка вывода"))
        self._output_mode_box.setItemText(0, t("converted/ рядом с исходником"))
        self._output_mode_box.setItemText(1, t("Фиксированная папка"))
        self._folder_label.setText(t("Фиксированная папка"))
        if not self._settings.fixed_output_dir:
            self._folder_btn.setText(t("Выбрать папку…"))
        self._conflict_label.setText(t("Конфликты имён"))
        self._conflict_box.setItemText(0, t("Добавлять суффикс (1)"))
        self._conflict_box.setItemText(1, t("Перезаписывать"))
        self._theme_label.setText(t("Тема"))
        self._theme_box.setItemText(0, t("Система"))
        self._theme_box.setItemText(1, t("Светлая"))
        self._theme_box.setItemText(2, t("Тёмная"))
        self._workers_label.setText(t("Максимум параллельных задач"))
        self._workers_box.setItemText(0, t("Авто"))
        self._codec_label.setText(t("Кодек видео по умолчанию"))
        for i, codec_id in enumerate(VIDEO_CODEC_IDS):
            self._codec_box.setItemText(i, t(VIDEO_CODEC_LABELS[codec_id]))

    def apply_theme(self, p: theme.Palette | None = None) -> None:
        p = p or theme.palette()
        self._title.setStyleSheet(theme.text_style(p.text_primary, 20, 700))
        self._panel.setStyleSheet(theme.panel_qss("SettingsPanel", p))
        for label in self._panel.findChildren(QLabel, "SettingLabel"):
            label.setStyleSheet(theme.text_style(p.text_secondary, 13, 400))
        for box in (
            self._language_box, self._output_mode_box, self._conflict_box,
            self._theme_box, self._codec_box,
        ):
            box.setStyleSheet(theme.input_qss(p))
        self._workers_box.setStyleSheet(theme.input_qss(p))
        self._folder_btn.setStyleSheet(theme.secondary_button_qss(p))
