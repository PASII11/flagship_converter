"""Карточка файла в очереди задач конвертации."""
from __future__ import annotations

import uuid
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from flagship_converter.core.models import JobStatus

# ---------------------------------------------------------------------------
# Константы форматов
# ---------------------------------------------------------------------------
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".gif"}
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".m4v"}
DOC_EXTS   = {".pdf", ".docx", ".md"}

OUTPUT_FORMATS: dict[str, list[str]] = {
    "image": ["webp", "jpg", "png", "bmp", "tiff"],
    "audio": ["mp3", "wav", "flac", "aac", "ogg"],
    "video": ["mp4", "mkv", "avi", "webm"],
    "doc":   ["pdf", "docx", "md"],
}

FILE_ICONS: dict[str, str] = {
    "image": "🖼",
    "audio": "🎵",
    "video": "🎬",
    "doc":   "📄",
    "unknown": "📁",
}

STATUS_CONFIG: dict[JobStatus, tuple[str, str]] = {
    JobStatus.PENDING:   ("Ожидание",     "#8B92B8"),
    JobStatus.RUNNING:   ("Конвертация…", "#7C83FD"),
    JobStatus.DONE:      ("✅ Готово",     "#4CAF50"),
    JobStatus.FAILED:    ("❌ Ошибка",     "#F44336"),
    JobStatus.CANCELLED: ("Отменено",     "#FFA726"),
}

CHUNK_COLORS: dict[JobStatus, str] = {
    JobStatus.DONE:      "#4CAF50",
    JobStatus.FAILED:    "#F44336",
    JobStatus.CANCELLED: "#FFA726",
}


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _get_category(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS: return "image"
    if ext in AUDIO_EXTS: return "audio"
    if ext in VIDEO_EXTS: return "video"
    if ext in DOC_EXTS:   return "doc"
    return "unknown"


def _fmt_size(size_bytes: int) -> str:
    if size_bytes < 1_024:
        return f"{size_bytes} B"
    if size_bytes < 1_024 ** 2:
        return f"{size_bytes / 1_024:.1f} KB"
    return f"{size_bytes / 1_024 ** 2:.1f} MB"


# ---------------------------------------------------------------------------
# FileCard
# ---------------------------------------------------------------------------

class FileCard(QFrame):
    """Карточка одного файла: иконка, имя, per-file настройки, прогресс."""

    remove_requested = Signal(str)  # card_id

    def __init__(self, file_path: Path, card_id: str | None = None) -> None:
        super().__init__()
        self.card_id   = card_id or str(uuid.uuid4())
        self.file_path = file_path
        self._category = _get_category(file_path)

        self._build_ui()
        self._update_settings_visibility(self._format_box.currentText())

    # ------------------------------------------------------------------
    # Построение UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "FileCard {"
            "  background-color: #1E2030;"
            "  border: 1px solid #2E3250;"
            "  border-radius: 8px;"
            "}"
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)

        # Иконка категории
        icon = QLabel(FILE_ICONS.get(self._category, "📁"))
        icon.setFixedSize(36, 36)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = icon.font(); f.setPointSize(18); icon.setFont(f)
        root.addWidget(icon)

        # Центральная колонка
        center = QVBoxLayout()
        center.setSpacing(4)

        # Строка имени + размер
        name_row = QHBoxLayout()
        self._name_label = QLabel(self.file_path.name)
        nf = self._name_label.font(); nf.setBold(True); self._name_label.setFont(nf)
        self._name_label.setStyleSheet("color: #E0E5FF;")
        try:
            size_str = _fmt_size(self.file_path.stat().st_size)
        except OSError:
            size_str = "—"
        size_lbl = QLabel(size_str)
        size_lbl.setStyleSheet("color: #5C6380; font-size: 11px;")
        name_row.addWidget(self._name_label)
        name_row.addWidget(size_lbl)
        name_row.addStretch()
        center.addLayout(name_row)

        # Строка настроек
        settings_row = QHBoxLayout()
        settings_row.setSpacing(6)

        settings_row.addWidget(QLabel("→"))

        self._format_box = QComboBox()
        self._format_box.setFixedWidth(80)
        self._format_box.addItems(OUTPUT_FORMATS.get(self._category, []))
        self._format_box.currentTextChanged.connect(self._update_settings_visibility)
        settings_row.addWidget(self._format_box)

        # Качество (изображения)
        self._quality_label = QLabel("Качество:")
        self._quality_label.setStyleSheet("color: #8B92B8; font-size: 11px;")
        self._quality_spin = QSpinBox()
        self._quality_spin.setRange(1, 95)
        self._quality_spin.setValue(85)
        self._quality_spin.setFixedWidth(55)
        settings_row.addWidget(self._quality_label)
        settings_row.addWidget(self._quality_spin)

        # Аудио битрейт
        self._audio_label = QLabel("Битрейт:")
        self._audio_label.setStyleSheet("color: #8B92B8; font-size: 11px;")
        self._audio_box = QComboBox()
        self._audio_box.addItems(["128k", "192k", "256k", "320k"])
        self._audio_box.setCurrentText("192k")
        self._audio_box.setFixedWidth(70)
        settings_row.addWidget(self._audio_label)
        settings_row.addWidget(self._audio_box)

        # Видео битрейт
        self._vbitrate_label = QLabel("Видео:")
        self._vbitrate_label.setStyleSheet("color: #8B92B8; font-size: 11px;")
        self._vbitrate_box = QComboBox()
        self._vbitrate_box.addItems(["1M", "2.5M", "5M", "10M", "20M"])
        self._vbitrate_box.setCurrentText("2.5M")
        self._vbitrate_box.setFixedWidth(70)
        settings_row.addWidget(self._vbitrate_label)
        settings_row.addWidget(self._vbitrate_box)

        # Видео кодек
        self._vcodec_label = QLabel("Кодек:")
        self._vcodec_label.setStyleSheet("color: #8B92B8; font-size: 11px;")
        self._vcodec_box = QComboBox()
        self._vcodec_box.addItems(
            ["Авто (CPU x264)", "AMD (AMF)", "NVIDIA (NVENC)", "Intel (QSV)"]
        )
        self._vcodec_box.setFixedWidth(135)
        settings_row.addWidget(self._vcodec_label)
        settings_row.addWidget(self._vcodec_box)

        settings_row.addStretch()

        # Статус (правый край)
        self._status_label = QLabel("Ожидание")
        self._status_label.setStyleSheet("color: #8B92B8; font-size: 11px;")
        self._status_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        settings_row.addWidget(self._status_label)
        center.addLayout(settings_row)

        # Прогресс-бар
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(4)
        self._apply_progress_style("#7C83FD")
        center.addWidget(self._progress_bar)

        root.addLayout(center)

        # Кнопка удаления
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setStyleSheet(
            "QPushButton { border: none; color: #5C6380; font-size: 14px;"
            "  border-radius: 12px; background: transparent; }"
            "QPushButton:hover { color: #F44336; background-color: #2A2D3E; }"
        )
        remove_btn.clicked.connect(lambda: self.remove_requested.emit(self.card_id))
        root.addWidget(remove_btn, alignment=Qt.AlignmentFlag.AlignTop)

    # ------------------------------------------------------------------
    # Логика видимости настроек
    # ------------------------------------------------------------------

    def _update_settings_visibility(self, fmt: str) -> None:
        cat = self._category
        is_img   = cat == "image"
        is_audio = cat == "audio"
        is_video = cat == "video"

        show_quality  = is_img and fmt not in ("png",)
        show_audio    = is_audio and fmt not in ("wav", "flac")
        show_video    = is_video
        show_codec    = is_video and fmt != "webm"

        self._quality_label.setVisible(show_quality)
        self._quality_spin.setVisible(show_quality)
        self._audio_label.setVisible(show_audio)
        self._audio_box.setVisible(show_audio)
        self._vbitrate_label.setVisible(show_video)
        self._vbitrate_box.setVisible(show_video)
        self._vcodec_label.setVisible(show_codec)
        self._vcodec_box.setVisible(show_codec)

    # ------------------------------------------------------------------
    # Вспомогательный метод стиля прогресс-бара
    # ------------------------------------------------------------------

    def _apply_progress_style(self, chunk_color: str) -> None:
        self._progress_bar.setStyleSheet(
            "QProgressBar { border: none; background-color: #2A2D3E; border-radius: 2px; }"
            f"QProgressBar::chunk {{ background-color: {chunk_color}; border-radius: 2px; }}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def target_ext(self) -> str:
        return self._format_box.currentText()

    @property
    def job_params(self) -> dict[str, object]:
        return {
            "quality":       self._quality_spin.value(),
            "lossless_webp": False,
            "audio_bitrate": self._audio_box.currentText(),
            "video_bitrate": self._vbitrate_box.currentText(),
            "video_codec":   self._vcodec_box.currentText(),
        }

    def is_convertible(self) -> bool:
        """True если для файла есть хотя бы один поддерживаемый формат вывода."""
        return bool(OUTPUT_FORMATS.get(self._category))

    def set_progress(self, percent: int) -> None:
        self._progress_bar.setValue(percent)

    def set_status(self, status: JobStatus) -> None:
        text, color = STATUS_CONFIG.get(status, ("—", "#8B92B8"))
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {color}; font-size: 11px;")
        chunk = CHUNK_COLORS.get(status, "#7C83FD")
        self._apply_progress_style(chunk)

    def lock_controls(self, locked: bool) -> None:
        """Блокировать/разблокировать настройки во время конвертации."""
        for w in (
            self._format_box, self._quality_spin, self._audio_box,
            self._vbitrate_box, self._vcodec_box,
        ):
            w.setEnabled(not locked)
