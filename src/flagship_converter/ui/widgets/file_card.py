"""File card widget for a single conversion task."""
from __future__ import annotations

import uuid
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
)

from flagship_converter.core.models import JobStatus
from flagship_converter.ui import theme

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


def _get_category(path: Path) -> str:
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


def _shorten_middle(value: str, max_chars: int = 68) -> str:
    if len(value) <= max_chars:
        return value
    head = max_chars // 2 - 2
    tail = max_chars - head - 3
    return f"{value[:head]}...{value[-tail:]}"


def _category_meta(category: str, p: theme.Palette) -> tuple[str, str, str, str, str]:
    if category == "image":
        return ("IMG", "Изображение", p.blue, p.blue_soft, p.border)
    if category == "audio":
        return ("AUD", "Аудио", p.orange, p.orange_soft, p.border)
    if category == "video":
        return ("VID", "Видео", p.accent, p.accent_soft, p.border)
    if category == "doc":
        return ("DOC", "Документ", p.green, p.green_soft, p.border)
    return ("FILE", "Неизвестный тип", p.text_secondary, p.surface_secondary, p.border)


def _status_meta(status: JobStatus, p: theme.Palette) -> tuple[str, str, str, str, str]:
    if status == JobStatus.RUNNING:
        return ("Конвертация", p.accent, p.accent_soft, p.border, p.accent)
    if status == JobStatus.DONE:
        return ("Готово", p.green, p.green_soft, p.border, p.green)
    if status == JobStatus.FAILED:
        return ("Ошибка", p.error, p.error_soft, p.border, p.error)
    if status == JobStatus.CANCELLED:
        return ("Отменено", p.orange, p.orange_soft, p.border, p.orange)
    return ("В очереди", p.text_secondary, p.surface_secondary, p.border, p.accent)


def _card_qss(p: theme.Palette) -> str:
    return f"""
QFrame#FileCard {{
    background-color: {p.surface_elevated};
    border: 1px solid {p.border};
    border-radius: 14px;
}}
QFrame#FileCard:hover {{
    border-color: {p.border_strong};
}}
QFrame#ResultStrip {{
    background-color: {p.surface_secondary};
    border: 1px solid {p.border};
    border-radius: 10px;
}}
"""


class FileCard(QFrame):
    """One file row: metadata, target format, progress, status and result actions."""

    remove_requested = Signal(str)

    def __init__(self, file_path: Path, card_id: str | None = None) -> None:
        super().__init__()
        self.card_id = card_id or str(uuid.uuid4())
        self.file_path = file_path
        self._category = _get_category(file_path)
        self._status = JobStatus.PENDING
        self._output_path: Path | None = None
        self._last_error: str | None = None

        self._build_ui()
        self._update_settings_visibility(self._format_box.currentText())
        if self.is_convertible():
            self.set_status(JobStatus.PENDING)
        else:
            self._apply_unsupported_state()
        self.apply_theme()

    def _build_ui(self) -> None:
        self.setObjectName("FileCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setSpacing(14)

        self._category_badge = QLabel()
        self._category_badge.setFixedSize(50, 42)
        self._category_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_row.addWidget(self._category_badge)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        self._name_label = QLabel(self.file_path.name)
        self._name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._name_label.setToolTip(str(self.file_path))

        try:
            size_str = _fmt_size(self.file_path.stat().st_size)
        except OSError:
            size_str = "размер неизвестен"

        self._category_label = _category_meta(self._category, theme.palette())[1]
        parent = _shorten_middle(str(self.file_path.parent), 58)
        self._meta_label = QLabel(f"{self._category_label} / {size_str} / {parent}")
        self._meta_label.setToolTip(str(self.file_path.parent))
        self._meta_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        title_col.addWidget(self._name_label)
        title_col.addWidget(self._meta_label)
        header_row.addLayout(title_col, stretch=1)

        self._status_label = QLabel()
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setMinimumWidth(112)
        header_row.addWidget(self._status_label)

        self._remove_btn = QPushButton("×")
        self._remove_btn.setFixedSize(32, 32)
        self._remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remove_btn.setToolTip("Убрать файл из очереди")
        self._remove_btn.clicked.connect(lambda: self.remove_requested.emit(self.card_id))
        header_row.addWidget(self._remove_btn)

        root.addLayout(header_row)

        settings_row = QHBoxLayout()
        settings_row.setSpacing(10)

        self._format_label = QLabel("Формат")
        settings_row.addWidget(self._format_label)

        self._format_box = QComboBox()
        self._format_box.setFixedWidth(96)
        self._format_box.addItems(OUTPUT_FORMATS.get(self._category, []))
        self._format_box.currentTextChanged.connect(self._update_settings_visibility)
        settings_row.addWidget(self._format_box)

        self._quality_label = QLabel("Качество")
        self._quality_spin = QSpinBox()
        self._quality_spin.setRange(1, 95)
        self._quality_spin.setValue(85)
        self._quality_spin.setFixedWidth(74)
        settings_row.addWidget(self._quality_label)
        settings_row.addWidget(self._quality_spin)

        self._audio_label = QLabel("Битрейт")
        self._audio_box = QComboBox()
        self._audio_box.addItems(["128k", "192k", "256k", "320k"])
        self._audio_box.setCurrentText("192k")
        self._audio_box.setFixedWidth(84)
        settings_row.addWidget(self._audio_label)
        settings_row.addWidget(self._audio_box)

        self._vbitrate_label = QLabel("Видео")
        self._vbitrate_box = QComboBox()
        self._vbitrate_box.addItems(["1M", "2.5M", "5M", "10M", "20M"])
        self._vbitrate_box.setCurrentText("2.5M")
        self._vbitrate_box.setFixedWidth(86)
        settings_row.addWidget(self._vbitrate_label)
        settings_row.addWidget(self._vbitrate_box)

        self._vcodec_label = QLabel("Кодек")
        self._vcodec_box = QComboBox()
        self._vcodec_box.addItems(
            ["Авто (CPU x264)", "AMD (AMF)", "NVIDIA (NVENC)", "Intel (QSV)"]
        )
        self._vcodec_box.setFixedWidth(152)
        settings_row.addWidget(self._vcodec_label)
        settings_row.addWidget(self._vcodec_box)

        self._unsupported_label = QLabel("Тип файла пока не поддерживается")
        self._unsupported_label.setVisible(False)
        settings_row.addWidget(self._unsupported_label)

        settings_row.addStretch()
        root.addLayout(settings_row)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(6)
        root.addWidget(self._progress_bar)

        self._message_label = QLabel()
        self._message_label.setWordWrap(True)
        self._message_label.setVisible(False)
        root.addWidget(self._message_label)

        self._result_strip = QFrame()
        self._result_strip.setObjectName("ResultStrip")
        self._result_strip.setVisible(False)
        result_layout = QHBoxLayout(self._result_strip)
        result_layout.setContentsMargins(12, 8, 10, 8)
        result_layout.setSpacing(10)

        self._result_label = QLabel()
        self._result_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        result_layout.addWidget(self._result_label)

        self._open_file_btn = QPushButton("Открыть")
        self._open_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_file_btn.clicked.connect(self._open_output_file)
        result_layout.addWidget(self._open_file_btn)

        self._open_folder_btn = QPushButton("Папка")
        self._open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_folder_btn.clicked.connect(self._open_output_folder)
        result_layout.addWidget(self._open_folder_btn)

        root.addWidget(self._result_strip)

    def apply_theme(self, p: theme.Palette | None = None) -> None:
        p = p or theme.palette()
        code, label, fg, bg, border = _category_meta(self._category, p)
        self._category_label = label

        self.setStyleSheet(_card_qss(p))
        self._category_badge.setText(code)
        self._category_badge.setStyleSheet(theme.category_badge_style(fg, bg, border))
        self._name_label.setStyleSheet(theme.text_style(p.text_primary, 14, 720))
        self._meta_label.setStyleSheet(theme.text_style(p.text_secondary, 12, 420))
        self._format_label.setStyleSheet(theme.text_style(p.text_secondary, 12, 650))
        self._quality_label.setStyleSheet(theme.text_style(p.text_secondary, 12, 650))
        self._audio_label.setStyleSheet(theme.text_style(p.text_secondary, 12, 650))
        self._vbitrate_label.setStyleSheet(theme.text_style(p.text_secondary, 12, 650))
        self._vcodec_label.setStyleSheet(theme.text_style(p.text_secondary, 12, 650))
        self._unsupported_label.setStyleSheet(theme.text_style(p.orange, 12, 700))
        self._result_label.setStyleSheet(theme.text_style(p.text_secondary, 12, 620))
        self._remove_btn.setStyleSheet(theme.ghost_button_qss(p, danger=True))
        self._open_file_btn.setStyleSheet(theme.secondary_button_qss(p))
        self._open_folder_btn.setStyleSheet(theme.ghost_button_qss(p))

        input_style = theme.input_qss(p)
        for widget in (
            self._format_box,
            self._quality_spin,
            self._audio_box,
            self._vbitrate_box,
            self._vcodec_box,
        ):
            widget.setStyleSheet(input_style)

        self._style_status(p)
        self._style_message(p)
        self._style_progress(p)

    def _update_settings_visibility(self, fmt: str) -> None:
        is_img = self._category == "image"
        is_audio = self._category == "audio"
        is_video = self._category == "video"

        show_quality = is_img and fmt not in ("png",)
        show_audio = is_audio and fmt not in ("wav", "flac")
        show_video = is_video
        show_codec = is_video and fmt != "webm"

        self._quality_label.setVisible(show_quality)
        self._quality_spin.setVisible(show_quality)
        self._audio_label.setVisible(show_audio)
        self._audio_box.setVisible(show_audio)
        self._vbitrate_label.setVisible(show_video)
        self._vbitrate_box.setVisible(show_video)
        self._vcodec_label.setVisible(show_codec)
        self._vcodec_box.setVisible(show_codec)

    def _apply_unsupported_state(self) -> None:
        self._format_label.setVisible(False)
        self._format_box.setVisible(False)
        self._unsupported_label.setVisible(True)
        self._progress_bar.setEnabled(False)
        self._message_label.setText(
            "Добавьте файл изображения, аудио, видео, PDF, DOCX или Markdown."
        )
        self._message_label.setVisible(True)

    def _style_status(self, p: theme.Palette | None = None) -> None:
        p = p or theme.palette()
        text, fg, bg, border, _progress = _status_meta(self._status, p)
        if not self.is_convertible():
            text, fg, bg, border = ("Не поддерживается", p.orange, p.orange_soft, p.border)
        self._status_label.setText(text)
        self._status_label.setStyleSheet(theme.status_pill_style(fg, bg, border))

    def _style_progress(self, p: theme.Palette | None = None) -> None:
        p = p or theme.palette()
        _text, _fg, _bg, _border, progress = _status_meta(self._status, p)
        self._progress_bar.setStyleSheet(theme.progress_qss(progress, p))

    def _style_message(self, p: theme.Palette | None = None) -> None:
        p = p or theme.palette()
        if self._last_error:
            self._message_label.setStyleSheet(theme.text_style(p.error, 12, 650))
        elif self._status == JobStatus.CANCELLED:
            self._message_label.setStyleSheet(theme.text_style(p.orange, 12, 650))
        else:
            self._message_label.setStyleSheet(theme.text_style(p.text_secondary, 12, 500))

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
            "quality": self._quality_spin.value(),
            "lossless_webp": False,
            "audio_bitrate": self._audio_box.currentText(),
            "video_bitrate": self._vbitrate_box.currentText(),
            "video_codec": self._vcodec_box.currentText(),
        }

    def is_convertible(self) -> bool:
        """True when at least one output format is available for the file."""
        return bool(OUTPUT_FORMATS.get(self._category))

    def set_output_path(self, output_path: Path) -> None:
        self._output_path = output_path
        if self._status == JobStatus.DONE:
            self._show_result_actions()

    def set_progress(self, percent: int) -> None:
        self._progress_bar.setValue(max(0, min(percent, 100)))

    def set_status(self, status: JobStatus) -> None:
        self._status = status
        self._last_error = None
        self._style_status()
        self._style_progress()
        self._style_message()

        if status in (JobStatus.PENDING, JobStatus.RUNNING):
            self._message_label.setVisible(False)
            self._result_strip.setVisible(False)
        elif status == JobStatus.DONE:
            self._message_label.setVisible(False)
            self._show_result_actions()
        elif status == JobStatus.CANCELLED:
            self._result_strip.setVisible(False)
            self._message_label.setText("Операция отменена. Файл можно запустить снова.")
            self._message_label.setVisible(True)

    def set_error(self, error: str) -> None:
        self._last_error = error
        self._status = JobStatus.FAILED
        self._style_status()
        self._style_progress()
        self._style_message()
        self._result_strip.setVisible(False)
        short_error = _shorten_middle(error.replace("\n", " "), 140)
        self._message_label.setText(f"Не удалось конвертировать: {short_error}")
        self._message_label.setToolTip(error)
        self._message_label.setVisible(True)

    def lock_controls(self, locked: bool) -> None:
        controls_enabled = (not locked) and self.is_convertible()
        for widget in (
            self._format_box,
            self._quality_spin,
            self._audio_box,
            self._vbitrate_box,
            self._vcodec_box,
        ):
            widget.setEnabled(controls_enabled)

        self._remove_btn.setEnabled(not locked)
        result_enabled = (
            (not locked)
            and self._status == JobStatus.DONE
            and self._output_path is not None
        )
        self._open_file_btn.setEnabled(result_enabled)
        self._open_folder_btn.setEnabled(result_enabled)

    def _show_result_actions(self) -> None:
        if self._output_path is None:
            self._result_strip.setVisible(False)
            return
        display = _shorten_middle(str(self._output_path), 92)
        self._result_label.setText(f"Результат: {display}")
        self._result_label.setToolTip(str(self._output_path))
        self._result_strip.setVisible(True)
        exists = self._output_path.exists()
        self._open_file_btn.setEnabled(exists)
        self._open_folder_btn.setEnabled(self._output_path.parent.exists())

    def _open_output_file(self) -> None:
        if self._output_path and self._output_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._output_path)))

    def _open_output_folder(self) -> None:
        if self._output_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._output_path.parent)))
