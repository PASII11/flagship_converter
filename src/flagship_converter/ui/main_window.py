"""Главное окно приложения."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from flagship_converter.core.engine import ConversionEngine
from flagship_converter.ui.widgets.drop_zone import DropZone
from flagship_converter.ui.widgets.job_item import JobItemWidget
from flagship_converter.ui.workers import PlanRunner


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Flagship File Converter")
        self.setMinimumSize(850, 600)

        self._engine = ConversionEngine()
        self._output_dir: Path | None = None
        self._dropped_files: list[str] = []
        self._cancel_flag: list[bool] = [False]
        self._job_widgets: dict[str, JobItemWidget] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self._drop_zone = DropZone()
        self._drop_zone.files_dropped.connect(self._on_files_dropped)
        layout.addWidget(self._drop_zone)

        # --- Settings bar 1 ---
        settings_bar = QHBoxLayout()

        settings_bar.addWidget(QLabel("Формат:"))
        self._format_box = QComboBox()
        self._format_box.addItems([
            "webp", "jpg", "png",
            "mp3", "wav", "flac", "aac", "ogg",
            "mp4", "mkv", "avi", "webm",
            "pdf", "docx", "md"
        ])
        self._format_box.currentTextChanged.connect(self._on_format_changed)
        settings_bar.addWidget(self._format_box)

        self._quality_label = QLabel("Качество:")
        self._quality_spin = QSpinBox()
        self._quality_spin.setRange(1, 95)
        self._quality_spin.setValue(85)
        settings_bar.addWidget(self._quality_label)
        settings_bar.addWidget(self._quality_spin)

        self._lossless_cb = QCheckBox("Lossless")
        settings_bar.addWidget(self._lossless_cb)

        self._audio_bitrate_label = QLabel("Аудио:")
        self._audio_bitrate_box = QComboBox()
        self._audio_bitrate_box.addItems(["128k", "192k", "256k", "320k"])
        self._audio_bitrate_box.setCurrentText("192k")
        settings_bar.addWidget(self._audio_bitrate_label)
        settings_bar.addWidget(self._audio_bitrate_box)

        self._video_bitrate_label = QLabel("Видео:")
        self._video_bitrate_box = QComboBox()
        self._video_bitrate_box.addItems(["1M", "2.5M", "5M", "10M", "20M"])
        self._video_bitrate_box.setCurrentText("2.5M")
        settings_bar.addWidget(self._video_bitrate_label)
        settings_bar.addWidget(self._video_bitrate_box)

        self._video_codec_label = QLabel("Кодек:")
        self._video_codec_box = QComboBox()
        self._video_codec_box.addItems(
            ["Авто (CPU x264)", "AMD (AMF)", "NVIDIA (NVENC)", "Intel (QSV)"]
        )
        settings_bar.addWidget(self._video_codec_label)
        settings_bar.addWidget(self._video_codec_box)

        settings_bar.addStretch()
        layout.addLayout(settings_bar)

        # --- Settings bar 2 ---
        folder_bar = QHBoxLayout()
        self._overwrite_cb = QCheckBox("Перезаписать если существует")
        folder_bar.addWidget(self._overwrite_cb)

        self._folder_btn = QPushButton("Выбрать папку…")
        self._folder_btn.clicked.connect(self._choose_output_dir)
        self._folder_label = QLabel("Папка: (по умолчанию — рядом с файлами)")
        folder_bar.addWidget(self._folder_btn)
        folder_bar.addWidget(self._folder_label)
        folder_bar.addStretch()
        layout.addLayout(folder_bar)

        # --- Action buttons ---
        btn_bar = QHBoxLayout()
        self._convert_btn = QPushButton("▶  Конвертировать")
        self._convert_btn.setEnabled(False)
        self._convert_btn.clicked.connect(self._start_conversion)
        self._cancel_btn = QPushButton("✕  Отмена")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel_conversion)
        btn_bar.addWidget(self._convert_btn)
        btn_bar.addWidget(self._cancel_btn)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        self._job_list = QListWidget()
        self._job_list.setSpacing(4)
        layout.addWidget(self._job_list)

        self.statusBar().showMessage("Перетащите файлы для начала работы")
        self._on_format_changed(self._format_box.currentText())

    def _on_format_changed(self, fmt: str) -> None:
        is_photo = fmt in ("jpg", "webp", "png")
        is_audio = fmt in ("mp3", "wav", "flac", "aac", "ogg")
        is_video = fmt in ("mp4", "mkv", "avi", "webm")

        self._quality_label.setVisible(is_photo and fmt != "png")
        self._quality_spin.setVisible(is_photo and fmt != "png")
        self._lossless_cb.setVisible(fmt == "webp")

        self._audio_bitrate_label.setVisible(is_audio and fmt not in ("wav", "flac"))
        self._audio_bitrate_box.setVisible(is_audio and fmt not in ("wav", "flac"))

        self._video_bitrate_label.setVisible(is_video)
        self._video_bitrate_box.setVisible(is_video)
        self._video_codec_label.setVisible(is_video and fmt != "webm")
        self._video_codec_box.setVisible(is_video and fmt != "webm")

    def _on_files_dropped(self, paths: list[str]) -> None:
        self._dropped_files = paths
        self._job_list.clear()
        self._job_widgets.clear()

        for p in paths:
            item = QListWidgetItem(self._job_list)
            widget = JobItemWidget(Path(p).name, self._format_box.currentText())
            item.setSizeHint(widget.sizeHint())
            self._job_list.addItem(item)
            self._job_list.setItemWidget(item, widget)

        self._convert_btn.setEnabled(bool(paths))
        self.statusBar().showMessage(f"Файлов добавлено: {len(paths)}")

    def _choose_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
        if folder:
            self._output_dir = Path(folder)
            self._folder_label.setText(f"Папка: {folder}")

    def _start_conversion(self) -> None:
        if not self._dropped_files:
            return

        output_dir = self._output_dir or (Path(self._dropped_files[0]).parent / "converted")
        target_ext = self._format_box.currentText()
        plan = self._engine.build_plan(
            paths=self._dropped_files,
            output_dir=output_dir,
            target_ext=target_ext,
            overwrite=self._overwrite_cb.isChecked(),
            quality=self._quality_spin.value(),
            lossless_webp=self._lossless_cb.isChecked(),
            audio_bitrate=self._audio_bitrate_box.currentText(),
            video_bitrate=self._video_bitrate_box.currentText(),
            video_codec=self._video_codec_box.currentText(),
        )

        if not plan.jobs:
            self.statusBar().showMessage("Нет файлов для конвертации (неподдерживаемые форматы?)")
            return

        self._job_list.clear()
        self._job_widgets.clear()
        for job in plan.jobs:
            item = QListWidgetItem(self._job_list)
            widget = JobItemWidget(job.input_path.name, target_ext)
            item.setSizeHint(widget.sizeHint())
            self._job_list.addItem(item)
            self._job_list.setItemWidget(item, widget)
            self._job_widgets[job.id] = widget

        self._cancel_flag[0] = False
        self._convert_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self.statusBar().showMessage(f"Конвертация {plan.total} файлов…")

        runner = PlanRunner(plan, self._engine, self._cancel_flag)
        runner.signals.job_started.connect(self._on_job_started)
        runner.signals.job_progress.connect(self._on_job_progress)
        runner.signals.job_finished.connect(self._on_job_finished)
        runner.signals.job_failed.connect(self._on_job_failed)
        runner.signals.all_done.connect(self._on_all_done)
        QThreadPool.globalInstance().start(runner)

    def _cancel_conversion(self) -> None:
        self._cancel_flag[0] = True
        self._cancel_btn.setEnabled(False)
        self.statusBar().showMessage("Отмена…")

    def _on_job_started(self, job_id: str) -> None:
        if widget := self._job_widgets.get(job_id):
            widget.set_status("🔄 Конвертация...", "#7C83FD")

    def _on_job_progress(self, job_id: str, percent: int) -> None:
        if widget := self._job_widgets.get(job_id):
            widget.set_progress(percent)

    def _on_job_finished(self, job_id: str) -> None:
        if widget := self._job_widgets.get(job_id):
            widget.set_progress(100)
            widget.set_status("✅ Готово", "#4CAF50")

    def _on_job_failed(self, job_id: str, error: str) -> None:
        if widget := self._job_widgets.get(job_id):
            widget.set_status("❌ Ошибка", "#F44336")

    def _on_all_done(self) -> None:
        self._convert_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self.statusBar().showMessage("Готово! Проверьте папку назначения.")
