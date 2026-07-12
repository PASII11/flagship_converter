"""Страница-верстак: командная строка, очередь, футер."""
from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from flagship_converter.core.engine import ConversionEngine
from flagship_converter.core.expand import expand_input_paths
from flagship_converter.core.models import ConversionPlan, JobStatus
from flagship_converter.i18n import t
from flagship_converter.ui import theme
from flagship_converter.ui.presets import PresetStore
from flagship_converter.ui.settings import AppSettings
from flagship_converter.ui.widgets.command_bar import CommandBar
from flagship_converter.ui.widgets.file_row import FileRow
from flagship_converter.ui.widgets.task_queue import TaskQueue
from flagship_converter.ui.workers import PlanRunner

MAX_FILES_WITHOUT_CONFIRM = 500


class ConverterPage(QWidget):
    def __init__(
        self,
        engine: ConversionEngine,
        settings: AppSettings,
        store: PresetStore,
    ) -> None:
        super().__init__()
        self._engine = engine
        self._settings = settings
        self._store = store
        self._converting = False
        self._cancel_event: threading.Event | None = None
        self._active_runner: PlanRunner | None = None
        self._job_row_map: dict[str, str] = {}
        self._progress_by_job: dict[str, int] = {}
        self._build_ui()
        self._queue.default_video_codec = settings.default_video_codec
        self._queue.set_presets(store.presets())
        settings.changed.connect(self._on_settings_changed)
        self.apply_theme()
        self._sync_controls()

    @property
    def is_converting(self) -> bool:
        return self._converting

    def _on_settings_changed(self) -> None:
        self._sync_folder_text()
        self._queue.default_video_codec = self._settings.default_video_codec

    def _build_ui(self) -> None:
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(theme.SPACING["lg"])

        self._command_bar = CommandBar()
        self._command_bar.add_files_clicked.connect(self._pick_files)
        self._command_bar.add_folder_clicked.connect(self._pick_add_folder)
        self._command_bar.folder_clicked.connect(self._pick_folder)
        self._command_bar.convert_clicked.connect(self._start_conversion)
        self._command_bar.cancel_clicked.connect(self._cancel_conversion)
        col.addWidget(self._command_bar)

        self._queue = TaskQueue()
        self._queue.files_changed.connect(self._on_files_changed)
        self._queue.add_clicked.connect(self._pick_files)
        self._queue.add_folder_clicked.connect(self._pick_add_folder)
        col.addWidget(self._queue, stretch=1)

        footer = QWidget()
        f = QHBoxLayout(footer)
        f.setContentsMargins(theme.SPACING["xs"], 0, theme.SPACING["xs"], 0)
        f.setSpacing(theme.SPACING["md"])
        self._footer_label = QLabel(t("Добавьте файлы или папки, или перетащите их в окно"))
        self._overall = QProgressBar()
        self._overall.setRange(0, 100)
        self._overall.setTextVisible(False)
        self._overall.setFixedHeight(4)
        self._percent_label = QLabel("")
        self._open_folder_btn = QPushButton(t("Открыть папку вывода"))
        self._open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_folder_btn.setVisible(False)
        self._open_folder_btn.clicked.connect(self._open_output_folder)
        f.addWidget(self._footer_label)
        f.addWidget(self._overall, stretch=1)
        f.addWidget(self._percent_label)
        f.addWidget(self._open_folder_btn)
        col.addWidget(footer)

        self._store.changed.connect(
            lambda: self._queue.set_presets(self._store.presets())
        )
        self._sync_folder_text()


    def add_files(self, paths: list[str]) -> None:
        if self._converting:
            return
        expanded = expand_input_paths(
            paths, self._engine.supported_input_extensions()
        )
        if len(expanded) > MAX_FILES_WITHOUT_CONFIRM:
            answer = QMessageBox.question(
                self,
                t("Добавить папку"),
                t("Найдено {n} файлов. Добавить все?").format(n=len(expanded)),
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        had_dirs = any(Path(p).is_dir() for p in paths)
        from_dirs = any(e.source_root is not None for e in expanded)
        self._queue.add_files(expanded)
        if had_dirs and not from_dirs:
            self._footer_label.setText(
                t("В папке не найдено поддерживаемых файлов")
            )

    def apply_preset_by_id(self, preset_id: str) -> None:
        preset = self._store.get(preset_id) if preset_id else None
        if preset:
            self._queue.apply_preset(preset)

    def _pick_files(self) -> None:
        if self._converting:
            return
        paths, _ = QFileDialog.getOpenFileNames(
            self, t("Выберите файлы для конвертации")
        )
        if paths:
            self.add_files(paths)

    def _pick_add_folder(self) -> None:
        if self._converting:
            return
        folder = QFileDialog.getExistingDirectory(
            self, t("Выберите папку с файлами")
        )
        if folder:
            self.add_files([folder])

    def _pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, t("Выберите папку для сохранения")
        )
        if folder:
            self._settings.output_mode = "fixed"
            self._settings.fixed_output_dir = folder
            self._sync_folder_text()

    def _sync_folder_text(self) -> None:
        if self._settings.output_mode == "fixed" and self._settings.fixed_output_dir:
            self._command_bar.set_folder_text(self._settings.fixed_output_dir)
        else:
            self._command_bar.set_folder_text(t("converted/ рядом с исходником"))

    def _output_dir_for(self, row: FileRow) -> Path:
        if self._settings.output_mode == "fixed" and self._settings.fixed_output_dir:
            base = Path(self._settings.fixed_output_dir)
            if row.rel_subdir is not None:
                return base / row.rel_subdir
            return base
        return row.file_path.parent / "converted"

    def _on_files_changed(self, _count: int) -> None:
        self._sync_controls()

    def _sync_controls(self) -> None:
        convertible = self._queue.pending_count()
        self._command_bar.set_convert_count(convertible)
        self._command_bar.set_convert_enabled(
            convertible > 0 and not self._converting
        )
        if self._queue.count() == 0:
            self._footer_label.setText(
                t("Добавьте файлы или папки, или перетащите их в окно")
            )
            self._overall.setValue(0)
            self._percent_label.setText("")
            self._open_folder_btn.setVisible(False)


    def _start_conversion(self) -> None:
        if self._converting:
            return
        plan = ConversionPlan()
        self._job_row_map.clear()
        self._progress_by_job.clear()
        reserved: set[Path] = set()
        for row in self._queue.rows():
            if not row.is_convertible() or row.status == JobStatus.DONE:
                continue
            job = self._engine.build_job(
                file_path=row.file_path,
                output_dir=self._output_dir_for(row),
                target_ext=row.target_ext,
                overwrite=self._settings.overwrite,
                params=row.job_params,
                reserved_outputs=reserved,
            )
            if job:
                plan.jobs.append(job)
                self._job_row_map[job.id] = row.card_id
                self._progress_by_job[job.id] = 0
                row.set_output_path(job.output_path)
                row.set_status(JobStatus.PENDING)
                row.set_progress(0)
            else:
                row.set_error(t("Выбранный формат недоступен для этого файла."))
        if not plan.jobs:
            self._footer_label.setText(t("Нет поддерживаемых файлов для конвертации"))
            return

        self._cancel_event = threading.Event()
        self._set_converting(True)
        runner = PlanRunner(plan, self._engine, self._cancel_event)
        self._active_runner = runner
        runner.signals.job_started.connect(self._on_job_started)
        runner.signals.job_progress.connect(self._on_job_progress)
        runner.signals.job_finished.connect(self._on_job_finished)
        runner.signals.job_failed.connect(self._on_job_failed)
        runner.signals.job_cancelled.connect(self._on_job_cancelled)
        runner.signals.all_done.connect(self._on_all_done)
        QThreadPool.globalInstance().start(runner)

    def _cancel_conversion(self) -> None:
        if self._cancel_event:
            self._cancel_event.set()
        self._footer_label.setText(t("Останавливаю текущие задачи…"))

    def _set_converting(self, converting: bool) -> None:
        self._converting = converting
        self._command_bar.set_converting(converting)
        self._queue.lock_all(converting)
        if not converting:
            self._sync_controls()

    def _row_for(self, job_id: str):
        card_id = self._job_row_map.get(job_id)
        return self._queue.get_row(card_id) if card_id else None

    def _on_job_started(self, job_id: str) -> None:
        self._progress_by_job[job_id] = max(
            self._progress_by_job.get(job_id, 0), 1
        )
        if row := self._row_for(job_id):
            row.set_status(JobStatus.RUNNING)
        self._update_overall()

    def _on_job_progress(self, job_id: str, percent: int) -> None:
        self._progress_by_job[job_id] = max(0, min(percent, 100))
        if row := self._row_for(job_id):
            row.set_progress(percent)
        self._update_overall()

    def _on_job_finished(self, job_id: str) -> None:
        self._progress_by_job[job_id] = 100
        if row := self._row_for(job_id):
            row.set_progress(100)
            row.set_status(JobStatus.DONE)
            if row.output_path:
                row.set_output_path(row.output_path)
        self._update_overall()

    def _on_job_failed(self, job_id: str, error: str) -> None:
        self._progress_by_job[job_id] = 100
        if row := self._row_for(job_id):
            row.set_progress(100)
            row.set_error(error)
        self._update_overall()

    def _on_job_cancelled(self, job_id: str) -> None:
        self._progress_by_job[job_id] = 100
        if row := self._row_for(job_id):
            row.set_status(JobStatus.CANCELLED)
        self._update_overall()

    def _on_all_done(self) -> None:
        self._set_converting(False)
        self._active_runner = None
        self._cancel_event = None
        statuses = [
            row.status
            for card_id in self._job_row_map.values()
            if (row := self._queue.get_row(card_id))
        ]
        done = sum(1 for s in statuses if s == JobStatus.DONE)
        failed = sum(1 for s in statuses if s == JobStatus.FAILED)
        cancelled = sum(1 for s in statuses if s == JobStatus.CANCELLED)
        parts = [t("Готово {done}").format(done=done)]
        if failed:
            parts.append(t("Ошибки {failed}").format(failed=failed))
        if cancelled:
            parts.append(t("Отменено {cancelled}").format(cancelled=cancelled))
        self._footer_label.setText(" · ".join(parts))
        if statuses:
            self._overall.setValue(100)
            self._percent_label.setText("100%")
            self._open_folder_btn.setVisible(done > 0)

    def _update_overall(self) -> None:
        if not self._progress_by_job:
            self._overall.setValue(0)
            self._percent_label.setText("")
            return
        percent = round(
            sum(self._progress_by_job.values()) / len(self._progress_by_job)
        )
        self._overall.setValue(percent)
        self._percent_label.setText(f"{percent}%")
        running = sum(
            1 for card_id in self._job_row_map.values()
            if (r := self._queue.get_row(card_id))
            and r.status == JobStatus.RUNNING
        )
        done = sum(
            1 for card_id in self._job_row_map.values()
            if (r := self._queue.get_row(card_id))
            and r.status == JobStatus.DONE
        )
        self._footer_label.setText(
            t("Готово {done} · В работе {running}").format(done=done, running=running)
        )

    def _open_output_folder(self) -> None:
        for card_id in self._job_row_map.values():
            row = self._queue.get_row(card_id)
            if row and row.status == JobStatus.DONE and row.output_path:
                QDesktopServices.openUrl(
                    QUrl.fromLocalFile(str(row.output_path.parent))
                )
                return

    def retranslate(self) -> None:
        self._command_bar.retranslate()
        self._queue.retranslate()
        self._sync_folder_text()
        self._sync_controls()

    def apply_theme(self, p: theme.Palette | None = None) -> None:
        p = p or theme.palette()
        self._command_bar.apply_theme(p)
        self._queue.apply_theme(p)
        self._footer_label.setStyleSheet(theme.text_style(p.text_secondary, 12, 400))
        self._percent_label.setStyleSheet(theme.text_style(p.text_secondary, 13, 600))
        self._overall.setStyleSheet(theme.progress_qss(p.running, p))
        self._open_folder_btn.setStyleSheet(theme.secondary_button_qss(p))
