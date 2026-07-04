"""Компактная строка очереди с раскрываемыми настройками."""
from __future__ import annotations

import uuid
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

from flagship_converter.core.models import JobStatus
from flagship_converter.ui import theme
from flagship_converter.ui.presets import Preset

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".gif"}
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".m4v"}
DOC_EXTS = {".pdf", ".docx", ".md"}

OUTPUT_FORMATS: dict[str, list[str]] = {
    "image": ["webp", "jpg", "png", "bmp", "tiff"],
    "audio": ["mp3", "wav", "flac", "aac", "ogg"],
    "video": ["mp4", "mkv", "avi", "webm"],
    "doc": ["pdf", "docx", "md"],
}

CATEGORY_TITLES = {
    "image": "Изображение", "audio": "Аудио",
    "video": "Видео", "doc": "Документ", "unknown": "Неизвестный тип",
}


def get_category(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in DOC_EXTS:
        return "doc"
    return "unknown"


def _fmt_size(size_bytes: int) -> str:
    if size_bytes < 1_024:
        return f"{size_bytes} B"
    if size_bytes < 1_024**2:
        return f"{size_bytes / 1_024:.1f} KB"
    if size_bytes < 1_024**3:
        return f"{size_bytes / 1_024**2:.1f} MB"
    return f"{size_bytes / 1_024**3:.1f} GB"


def _category_color(category: str, p: theme.Palette) -> str:
    return {
        "image": p.cat_image, "audio": p.cat_audio,
        "video": p.cat_video, "doc": p.cat_doc,
    }.get(category, p.text_muted)


class FileRow(QFrame):
    remove_requested = Signal(str)
    format_changed = Signal(str)

    def __init__(
        self,
        file_path: Path,
        card_id: str | None = None,
        default_video_codec: str | None = None,
    ) -> None:
        super().__init__()
        self.card_id = card_id or str(uuid.uuid4())
        self.file_path = file_path
        self.category = get_category(file_path)
        self._status = JobStatus.PENDING
        self._output_path: Path | None = None
        self._last_error: str | None = None
        self._overridden = False
        self._expanded = False
        self._applying = False
        self._presets: list[Preset] = []
        self._build_ui()
        if default_video_codec:
            self._applying = True
            try:
                self._codec.setCurrentText(default_video_codec)
            finally:
                self._applying = False
        self.apply_theme()
        self.set_expanded(True)


    def _build_ui(self) -> None:
        self.setObjectName("FileRow")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        head = QWidget()
        head.setFixedHeight(48)
        h = QHBoxLayout(head)
        h.setContentsMargins(theme.SPACING["lg"], 0, theme.SPACING["md"], 0)
        h.setSpacing(theme.SPACING["md"])

        self._dot = QLabel()
        self._dot.setFixedSize(10, 10)

        self._name = QLabel(self.file_path.name)
        self._name.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self._name.setToolTip(str(self.file_path))
        try:
            size = _fmt_size(self.file_path.stat().st_size)
        except OSError:
            size = "—"
        self._meta = QLabel(f"{CATEGORY_TITLES[self.category]} · {size}")

        self._format_box = QComboBox()
        self._format_box.addItems(OUTPUT_FORMATS.get(self.category, []))
        self._format_box.setFixedWidth(92)
        self._format_box.currentTextChanged.connect(self._on_user_format)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setTextVisible(False)
        self._progress.setFixedSize(90, 4)

        self._status_mark = QLabel("")
        self._status_mark.setFixedWidth(20)
        self._status_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._expand_btn = QPushButton("▾")
        self._expand_btn.setFixedSize(28, 28)
        self._expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._expand_btn.clicked.connect(
            lambda: self.set_expanded(not self._expanded)
        )

        self._remove_btn = QPushButton("×")
        self._remove_btn.setFixedSize(28, 28)
        self._remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remove_btn.setToolTip("Убрать файл из очереди")
        self._remove_btn.clicked.connect(
            lambda: self.remove_requested.emit(self.card_id)
        )

        h.addWidget(self._dot)
        h.addWidget(self._name, stretch=1)
        h.addWidget(self._meta)
        h.addWidget(self._format_box)
        h.addWidget(self._progress)
        h.addWidget(self._status_mark)
        h.addWidget(self._expand_btn)
        h.addWidget(self._remove_btn)
        root.addWidget(head)

        self._details = QWidget()
        self._details.setMaximumHeight(0)
        d = QVBoxLayout(self._details)
        d.setContentsMargins(
            theme.SPACING["lg"] + 22, theme.SPACING["sm"],
            theme.SPACING["md"], theme.SPACING["md"],
        )
        d.setSpacing(theme.SPACING["sm"])

        preset_row = QHBoxLayout()
        preset_row.setSpacing(theme.SPACING["sm"])
        self._preset_label = QLabel("Пресет")
        self._preset_box = QComboBox()
        self._preset_box.setMinimumWidth(160)
        self._preset_box.addItem("Свои настройки", "")
        self._preset_box.currentIndexChanged.connect(self._on_preset_chosen)
        preset_row.addWidget(self._preset_label)
        preset_row.addWidget(self._preset_box)
        preset_row.addStretch()
        d.addLayout(preset_row)

        params = QHBoxLayout()
        params.setSpacing(theme.SPACING["sm"])
        self._quality_label = QLabel("Качество")
        self._quality = QSpinBox()
        self._quality.setRange(1, 95)
        self._quality.setValue(85)
        self._quality.valueChanged.connect(self._mark_override)
        self._abitrate_label = QLabel("Битрейт аудио")
        self._abitrate = QComboBox()
        self._abitrate.addItems(["128k", "192k", "256k", "320k"])
        self._abitrate.setCurrentText("192k")
        self._abitrate.currentTextChanged.connect(self._mark_override)
        self._vbitrate_label = QLabel("Битрейт видео")
        self._vbitrate = QComboBox()
        self._vbitrate.addItems(["1M", "2.5M", "5M", "10M", "20M"])
        self._vbitrate.setCurrentText("2.5M")
        self._vbitrate.currentTextChanged.connect(self._mark_override)
        self._codec_label = QLabel("Кодек")
        self._codec = QComboBox()
        self._codec.addItems(
            ["Авто (CPU x264)", "AMD (AMF)", "NVIDIA (NVENC)", "Intel (QSV)"]
        )
        self._codec.currentTextChanged.connect(self._mark_override)
        for w in (
            self._quality_label, self._quality,
            self._abitrate_label, self._abitrate,
            self._vbitrate_label, self._vbitrate,
            self._codec_label, self._codec,
        ):
            params.addWidget(w)
        self._reset_btn = QPushButton("Сбросить к пресету")
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.clicked.connect(self.reset_override)
        params.addWidget(self._reset_btn)
        params.addStretch()
        d.addLayout(params)

        self._error_label = QLabel()
        self._error_label.setWordWrap(True)
        self._error_label.setVisible(False)
        self._copy_btn = QPushButton("Копировать текст ошибки")
        self._copy_btn.setVisible(False)
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.clicked.connect(self._copy_error)
        d.addWidget(self._error_label)
        d.addWidget(self._copy_btn)

        result = QHBoxLayout()
        result.setSpacing(theme.SPACING["sm"])
        self._result_label = QLabel()
        self._result_label.setVisible(False)
        self._open_btn = QPushButton("Открыть")
        self._open_btn.setVisible(False)
        self._open_btn.clicked.connect(self._open_file)
        self._folder_btn = QPushButton("Папка")
        self._folder_btn.setVisible(False)
        self._folder_btn.clicked.connect(self._open_folder)
        result.addWidget(self._result_label, stretch=1)
        result.addWidget(self._open_btn)
        result.addWidget(self._folder_btn)
        d.addLayout(result)

        root.addWidget(self._details)
        self._anim = QPropertyAnimation(self._details, b"maximumHeight")
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._sync_param_visibility(self._format_box.currentText())


    def _sync_param_visibility(self, fmt: str) -> None:
        is_img = self.category == "image"
        is_audio = self.category == "audio"
        is_video = self.category == "video"
        show_q = is_img and fmt != "png"
        show_a = is_audio and fmt not in ("wav", "flac")
        self._quality_label.setVisible(show_q)
        self._quality.setVisible(show_q)
        self._abitrate_label.setVisible(show_a)
        self._abitrate.setVisible(show_a)
        self._vbitrate_label.setVisible(is_video)
        self._vbitrate.setVisible(is_video)
        show_codec = is_video and fmt != "webm"
        self._codec_label.setVisible(show_codec)
        self._codec.setVisible(show_codec)

    def _on_user_format(self, fmt: str) -> None:
        self._sync_param_visibility(fmt)
        if not self._applying:
            self._overridden = True
            if self._status == JobStatus.DONE:
                self.set_progress(0)
                self.set_status(JobStatus.PENDING)
        self.format_changed.emit(self.category)

    def _mark_override(self, *_args: object) -> None:
        if not self._applying:
            self._overridden = True

    def set_target_format(self, ext: str) -> None:
        if ext not in OUTPUT_FORMATS.get(self.category, []):
            return
        self._applying = True
        try:
            self._format_box.setCurrentText(ext)
        finally:
            self._applying = False

    def apply_preset(self, preset: Preset) -> None:
        self._applying = True
        try:
            ext = preset.formats.get(self.category, "")
            if ext in OUTPUT_FORMATS.get(self.category, []):
                self._format_box.setCurrentText(ext)
            self._quality.setValue(preset.image_quality)
            self._abitrate.setCurrentText(preset.audio_bitrate)
            self._vbitrate.setCurrentText(preset.video_bitrate)
            self._codec.setCurrentText(preset.video_codec)
        finally:
            self._applying = False

    def set_presets(self, presets: list[Preset]) -> None:
        self._presets = list(presets)
        current = str(self._preset_box.currentData() or "")
        self._preset_box.blockSignals(True)
        self._preset_box.clear()
        self._preset_box.addItem("Свои настройки", "")
        for preset in presets:
            self._preset_box.addItem(preset.name, preset.id)
        self._preset_box.setCurrentIndex(
            max(0, self._preset_box.findData(current))
        )
        self._preset_box.blockSignals(False)

    def _on_preset_chosen(self, _index: int) -> None:
        preset_id = str(self._preset_box.currentData() or "")
        preset = next((p for p in self._presets if p.id == preset_id), None)
        if preset:
            self._overridden = False
            self.apply_preset(preset)

    def reset_override(self) -> None:
        self._overridden = False
        self._on_preset_chosen(self._preset_box.currentIndex())

    @property
    def is_overridden(self) -> bool:
        return self._overridden

    @property
    def status(self) -> JobStatus:
        return self._status

    @property
    def target_ext(self) -> str:
        if not self.is_convertible():
            return ""
        return self._format_box.currentText()

    @property
    def output_path(self) -> Path | None:
        return self._output_path

    @property
    def job_params(self) -> dict[str, object]:
        return {
            "quality": self._quality.value(),
            "lossless_webp": False,
            "audio_bitrate": self._abitrate.currentText(),
            "video_bitrate": self._vbitrate.currentText(),
            "video_codec": self._codec.currentText(),
        }

    def is_convertible(self) -> bool:
        return bool(OUTPUT_FORMATS.get(self.category))

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self._expand_btn.setText("▴" if expanded else "▾")
        target = self._details.sizeHint().height() if expanded else 0
        self._anim.stop()
        self._anim.setStartValue(self._details.height())
        self._anim.setEndValue(target)
        self._anim.start()

    def set_progress(self, percent: int) -> None:
        self._progress.setValue(max(0, min(percent, 100)))

    def set_status(self, status: JobStatus) -> None:
        self._status = status
        self._last_error = None
        self._error_label.setVisible(False)
        self._copy_btn.setVisible(False)
        self._style_status()

    def set_error(self, error: str) -> None:
        self._status = JobStatus.FAILED
        self._last_error = error
        self._error_label.setText(f"Не удалось конвертировать: {error}")
        self._error_label.setVisible(True)
        self._copy_btn.setVisible(True)
        self.set_expanded(True)
        self._style_status()

    def set_output_path(self, output_path: Path) -> None:
        self._output_path = output_path
        self._result_label.setText(str(output_path))
        self._result_label.setToolTip(str(output_path))
        visible = self._status == JobStatus.DONE
        self._result_label.setVisible(visible)
        self._open_btn.setVisible(visible)
        self._folder_btn.setVisible(visible)

    def lock_controls(self, locked: bool) -> None:
        enabled = (not locked) and self.is_convertible()
        for w in (
            self._format_box, self._quality, self._abitrate,
            self._vbitrate, self._codec, self._reset_btn,
            self._preset_box,
        ):
            w.setEnabled(enabled)
        self._remove_btn.setEnabled(not locked)


    def apply_theme(self, p: theme.Palette | None = None) -> None:
        p = p or theme.palette()
        color = _category_color(self.category, p)
        self.setStyleSheet(
            "QFrame#FileRow {"
            f"background-color: {p.surface};"
            f"border-bottom: 1px solid {p.border};"
            "}"
            "QFrame#FileRow:hover {"
            f"background-color: {p.surface_secondary};"
            "}"
        )
        self._dot.setStyleSheet(
            f"background-color: {color}; border-radius: 5px;"
        )
        self._name.setStyleSheet(theme.text_style(p.text_primary, 13, 600))
        self._meta.setStyleSheet(theme.text_style(p.text_muted, 12, 400))
        self._format_box.setStyleSheet(theme.input_qss(p))
        self._preset_box.setStyleSheet(theme.input_qss(p))
        self._preset_label.setStyleSheet(theme.text_style(p.text_secondary, 12, 400))
        for w in (self._quality, self._abitrate, self._vbitrate, self._codec):
            w.setStyleSheet(theme.input_qss(p))
        for lbl in (
            self._quality_label, self._abitrate_label,
            self._vbitrate_label, self._codec_label,
        ):
            lbl.setStyleSheet(theme.text_style(p.text_secondary, 12, 400))
        self._error_label.setStyleSheet(theme.text_style(p.error, 12, 400))
        self._result_label.setStyleSheet(theme.text_style(p.text_secondary, 12, 400))
        self._expand_btn.setStyleSheet(
            "QPushButton {"
            f"color: {p.text_secondary}; background-color: {p.surface_secondary};"
            f"border: 1px solid {p.border_strong};"
            f"border-radius: {theme.RADIUS['control']}px;"
            "padding: 0; min-height: 28px; font-size: 12px;"
            "}"
            "QPushButton:hover {"
            f"color: {p.text_primary}; border-color: {p.text_muted};"
            "}"
        )
        self._remove_btn.setStyleSheet(
            "QPushButton {"
            f"color: #FFFFFF; background-color: {p.error};"
            "border: none; padding: 0; min-height: 28px;"
            f"border-radius: {theme.RADIUS['control']}px;"
            "font-size: 15px; font-weight: 700;"
            "}"
            "QPushButton:hover {"
            f"background-color: {p.accent_pressed};"
            "}"
        )
        self._reset_btn.setStyleSheet(theme.ghost_button_qss(p))
        self._copy_btn.setStyleSheet(theme.secondary_button_qss(p))
        self._open_btn.setStyleSheet(theme.secondary_button_qss(p))
        self._folder_btn.setStyleSheet(theme.ghost_button_qss(p))
        self._style_status(p)

    def _style_status(self, p: theme.Palette | None = None) -> None:
        p = p or theme.palette()
        marks = {
            JobStatus.PENDING: ("", p.text_muted, p.text_muted),
            JobStatus.RUNNING: ("●", p.running, p.running),
            JobStatus.DONE: ("✓", p.success, p.success),
            JobStatus.FAILED: ("!", p.error, p.error),
            JobStatus.CANCELLED: ("–", p.warning, p.warning),
        }
        mark, fg, bar = marks[self._status]
        self._status_mark.setText(mark)
        self._status_mark.setStyleSheet(theme.text_style(fg, 13, 700))
        self._progress.setStyleSheet(theme.progress_qss(bar, p))


    def _copy_error(self) -> None:
        from PySide6.QtWidgets import QApplication
        if self._last_error:
            QApplication.clipboard().setText(self._last_error)

    def _open_file(self) -> None:
        if self._output_path and self._output_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._output_path)))

    def _open_folder(self) -> None:
        if self._output_path:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self._output_path.parent))
            )
