"""Страница пресетов: карточки и встроенный редактор."""
from __future__ import annotations

import uuid

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from flagship_converter.ui import theme
from flagship_converter.ui.presets import Preset, PresetStore
from flagship_converter.ui.widgets.file_row import OUTPUT_FORMATS

_CATEGORIES = ("image", "audio", "video", "doc")
_CATEGORY_LABELS = {
    "image": "Изображения", "audio": "Аудио",
    "video": "Видео", "doc": "Документы",
}


_NO_FORMAT = "—"


def _summary(preset: Preset) -> str:
    parts = [
        preset.formats[c] for c in _CATEGORIES if preset.formats.get(c)
    ]
    if preset.formats.get("image"):
        parts.append(f"качество {preset.image_quality}")
    if preset.formats.get("audio"):
        parts.append(preset.audio_bitrate)
    if preset.formats.get("video"):
        parts.append(preset.video_bitrate)
    return " · ".join(parts) if parts else "пустой пресет"


class PresetsPage(QWidget):
    apply_requested = Signal(str)

    def __init__(self, store: PresetStore) -> None:
        super().__init__()
        self._store = store
        self._cards: list[QFrame] = []
        self._editing_id: str | None = None
        self._editor_formats: dict[str, str] = {}
        self._build_ui()
        self._on_editor_category(0)
        self._rebuild_cards()
        self.apply_theme()
        store.changed.connect(self._rebuild_cards)

    def _build_ui(self) -> None:
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(theme.SPACING["lg"])

        header = QHBoxLayout()
        self._title = QLabel("Пресеты")
        self._new_btn = QPushButton("Новый пресет")
        self._new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_btn.clicked.connect(self._start_new)
        header.addWidget(self._title)
        header.addStretch()
        header.addWidget(self._new_btn)
        col.addLayout(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self._cards_col = QVBoxLayout(container)
        self._cards_col.setContentsMargins(0, 0, 6, 0)
        self._cards_col.setSpacing(theme.SPACING["md"])
        self._cards_col.addStretch()
        self._scroll.setWidget(container)
        col.addWidget(self._scroll, stretch=1)

        self._editor = QFrame()
        self._editor.setObjectName("PresetEditor")
        self._editor.setVisible(False)
        e = QVBoxLayout(self._editor)
        e.setContentsMargins(
            theme.SPACING["lg"], theme.SPACING["lg"],
            theme.SPACING["lg"], theme.SPACING["lg"],
        )
        e.setSpacing(theme.SPACING["md"])
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Название пресета")
        e.addWidget(self._name_edit)

        type_row = QHBoxLayout()
        type_row.setSpacing(theme.SPACING["sm"])
        self._cat_label = QLabel("Тип файлов")
        self._cat_box = QComboBox()
        for category in _CATEGORIES:
            self._cat_box.addItem(_CATEGORY_LABELS[category], category)
        self._cat_box.currentIndexChanged.connect(self._on_editor_category)
        self._fmt_label = QLabel("Формат")
        self._fmt_box = QComboBox()
        self._fmt_box.currentTextChanged.connect(self._on_editor_format)
        type_row.addWidget(self._cat_label)
        type_row.addWidget(self._cat_box)
        type_row.addWidget(self._fmt_label)
        type_row.addWidget(self._fmt_box)
        type_row.addStretch()
        e.addLayout(type_row)

        params_row = QHBoxLayout()
        params_row.setSpacing(theme.SPACING["sm"])
        self._quality_label = QLabel("Качество")
        self._quality = QSpinBox()
        self._quality.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self._quality.setRange(1, 95)
        self._quality.setValue(85)
        self._abitrate_label = QLabel("Битрейт аудио")
        self._abitrate = QComboBox()
        self._abitrate.addItems(["128k", "192k", "256k", "320k"])
        self._abitrate.setCurrentText("192k")
        self._vbitrate_label = QLabel("Битрейт видео")
        self._vbitrate = QComboBox()
        self._vbitrate.addItems(["1M", "2.5M", "5M", "10M", "20M"])
        self._vbitrate.setCurrentText("2.5M")
        self._codec_label = QLabel("Кодек")
        self._codec = QComboBox()
        self._codec.addItems(
            ["Авто (CPU x264)", "AMD (AMF)", "NVIDIA (NVENC)", "Intel (QSV)"]
        )
        for w in (
            self._quality_label, self._quality,
            self._abitrate_label, self._abitrate,
            self._vbitrate_label, self._vbitrate,
            self._codec_label, self._codec,
        ):
            params_row.addWidget(w)
        params_row.addStretch()
        e.addLayout(params_row)

        buttons = QHBoxLayout()
        self._save_btn = QPushButton("Сохранить")
        self._save_btn.clicked.connect(self._save_editor)
        self._cancel_btn = QPushButton("Отмена")
        self._cancel_btn.clicked.connect(lambda: self._editor.setVisible(False))
        buttons.addStretch()
        buttons.addWidget(self._cancel_btn)
        buttons.addWidget(self._save_btn)
        e.addLayout(buttons)
        col.addWidget(self._editor)


    def _rebuild_cards(self) -> None:
        for card in self._cards:
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()
        for preset in self._store.presets():
            card = self._build_card(preset)
            self._cards_col.insertWidget(self._cards_col.count() - 1, card)
            self._cards.append(card)

    def _build_card(self, preset: Preset) -> QFrame:
        card = QFrame()
        card.setObjectName("PresetCard")
        row = QHBoxLayout(card)
        row.setContentsMargins(
            theme.SPACING["lg"], theme.SPACING["md"],
            theme.SPACING["lg"], theme.SPACING["md"],
        )
        row.setSpacing(theme.SPACING["md"])
        text_col = QVBoxLayout()
        name = QLabel(preset.name + ("  · встроенный" if preset.builtin else ""))
        name.setObjectName("PresetName")
        summary = QLabel(_summary(preset))
        summary.setObjectName("PresetSummary")
        text_col.addWidget(name)
        text_col.addWidget(summary)
        row.addLayout(text_col, stretch=1)

        apply_btn = QPushButton("Применить")
        apply_btn.clicked.connect(lambda _=False, i=preset.id: self._on_apply(i))
        dup_btn = QPushButton("Дублировать")
        dup_btn.clicked.connect(
            lambda _=False, i=preset.id: self._store.duplicate(i)
        )
        row.addWidget(apply_btn)
        row.addWidget(dup_btn)
        if not preset.builtin:
            edit_btn = QPushButton("Редактировать")
            edit_btn.clicked.connect(
                lambda _=False, i=preset.id: self._start_edit(i)
            )
            del_btn = QPushButton("Удалить")
            del_btn.clicked.connect(
                lambda _=False, i=preset.id: self._store.delete(i)
            )
            row.addWidget(edit_btn)
            row.addWidget(del_btn)
        card.setStyleSheet(self._card_qss())
        return card

    def _on_apply(self, preset_id: str) -> None:
        self.apply_requested.emit(preset_id)


    def _on_editor_category(self, _index: int) -> None:
        category = str(self._cat_box.currentData() or "image")
        self._fmt_box.blockSignals(True)
        self._fmt_box.clear()
        self._fmt_box.addItem(_NO_FORMAT)
        self._fmt_box.addItems(OUTPUT_FORMATS[category])
        self._fmt_box.setCurrentText(
            self._editor_formats.get(category, _NO_FORMAT)
        )
        self._fmt_box.blockSignals(False)
        self._sync_editor_params()

    def _on_editor_format(self, fmt: str) -> None:
        category = str(self._cat_box.currentData() or "")
        if not category:
            return
        if fmt and fmt != _NO_FORMAT:
            self._editor_formats[category] = fmt
        else:
            self._editor_formats.pop(category, None)
        self._sync_editor_params()

    def _sync_editor_params(self) -> None:
        category = str(self._cat_box.currentData() or "")
        enabled = category in self._editor_formats
        for w in (self._quality_label, self._quality):
            w.setVisible(enabled and category == "image")
        for w in (self._abitrate_label, self._abitrate):
            w.setVisible(enabled and category == "audio")
        for w in (
            self._vbitrate_label, self._vbitrate,
            self._codec_label, self._codec,
        ):
            w.setVisible(enabled and category == "video")

    def _start_new(self) -> None:
        self._editing_id = None
        self._name_edit.setText("")
        self._editor_formats = {}
        self._quality.setValue(85)
        self._abitrate.setCurrentText("192k")
        self._vbitrate.setCurrentText("2.5M")
        self._codec.setCurrentText("Авто (CPU x264)")
        self._cat_box.setCurrentIndex(0)
        self._on_editor_category(0)
        self._editor.setVisible(True)

    def _start_edit(self, preset_id: str) -> None:
        preset = self._store.get(preset_id)
        if preset is None or preset.builtin:
            return
        self._editing_id = preset_id
        self._name_edit.setText(preset.name)
        self._editor_formats = {
            c: f for c, f in preset.formats.items() if f
        }
        self._quality.setValue(preset.image_quality)
        self._abitrate.setCurrentText(preset.audio_bitrate)
        self._vbitrate.setCurrentText(preset.video_bitrate)
        self._codec.setCurrentText(preset.video_codec)
        self._cat_box.setCurrentIndex(0)
        self._on_editor_category(0)
        self._editor.setVisible(True)

    def _save_editor(self) -> None:
        name = self._name_edit.text().strip() or "Без названия"
        preset = Preset(
            id=self._editing_id or str(uuid.uuid4()),
            name=name,
            builtin=False,
            formats=dict(self._editor_formats),
            image_quality=self._quality.value(),
            audio_bitrate=self._abitrate.currentText(),
            video_bitrate=self._vbitrate.currentText(),
            video_codec=self._codec.currentText(),
        )
        if self._editing_id:
            self._store.update(preset)
        else:
            self._store.add(preset)
        self._editor.setVisible(False)


    def _card_qss(self) -> str:
        p = theme.palette()
        return (
            "QFrame#PresetCard {"
            f"background-color: {p.surface};"
            f"border: 1px solid {p.border};"
            f"border-radius: {theme.RADIUS['panel']}px;"
            "}"
            "QLabel#PresetName {"
            f"color: {p.text_primary}; font-size: 13px; font-weight: 600;"
            "}"
            "QLabel#PresetSummary {"
            f"color: {p.text_secondary}; font-size: 12px; font-weight: 400;"
            "}"
        )

    def apply_theme(self, p: theme.Palette | None = None) -> None:
        p = p or theme.palette()
        self._title.setStyleSheet(theme.text_style(p.text_primary, 20, 700))
        self._new_btn.setStyleSheet(theme.secondary_button_qss(p))
        self._scroll.setStyleSheet(theme.scroll_area_qss(p))
        self._editor.setStyleSheet(theme.panel_qss("PresetEditor", p))
        self._name_edit.setStyleSheet(theme.input_qss(p))
        for w in (
            self._cat_box, self._fmt_box,
            self._quality, self._abitrate, self._vbitrate, self._codec,
        ):
            w.setStyleSheet(theme.input_qss(p))
        for lbl in (
            self._cat_label, self._fmt_label, self._quality_label,
            self._abitrate_label, self._vbitrate_label, self._codec_label,
        ):
            lbl.setStyleSheet(theme.text_style(p.text_secondary, 12, 400))
        self._save_btn.setStyleSheet(theme.secondary_button_qss(p))
        self._cancel_btn.setStyleSheet(theme.ghost_button_qss(p))
        self._rebuild_cards()
