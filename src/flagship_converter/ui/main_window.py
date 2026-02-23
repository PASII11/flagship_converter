"""Главное окно приложения."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from flagship_converter.core.engine import ConversionEngine
from flagship_converter.core.models import ConversionPlan, JobStatus
from flagship_converter.ui.widgets.drop_zone import DropZone
from flagship_converter.ui.widgets.task_queue import TaskQueue
from flagship_converter.ui.workers import PlanRunner


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Flagship File Converter")
        self.setMinimumSize(900, 640)

        self._engine        = ConversionEngine()
        self._output_dir:  Path | None = None
        self._cancel_flag: list[bool]  = [False]

        # job_id → card_id: связь между задачами движка и карточками UI
        self._job_card_map: dict[str, str] = {}

        self._build_ui()

    # ------------------------------------------------------------------
    # Построение UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # --- Drop Zone ---
        self._drop_zone = DropZone()
        self._drop_zone.files_dropped.connect(self._on_files_dropped)
        self._drop_zone.setMaximumHeight(110)
        layout.addWidget(self._drop_zone)

        # --- Toolbar: Add Files / Clear All ---
        toolbar = QHBoxLayout()
        add_btn = QPushButton("➕ Добавить файлы")
        add_btn.clicked.connect(self._on_add_files_clicked)
        self._clear_btn = QPushButton("🗑 Очистить всё")
        self._clear_btn.clicked.connect(self._on_clear_all)
        self._clear_btn.setEnabled(False)
        toolbar.addWidget(add_btn)
        toolbar.addWidget(self._clear_btn)
        toolbar.addStretch()
        self._files_count_label = QLabel("Файлов: 0")
        self._files_count_label.setStyleSheet("color: #8B92B8;")
        toolbar.addWidget(self._files_count_label)
        layout.addLayout(toolbar)

        # --- Task Queue ---
        self._task_queue = TaskQueue()
        self._task_queue.files_changed.connect(self._on_files_changed)
        layout.addWidget(self._task_queue, stretch=1)

        # --- Нижняя панель: папка + перезапись ---
        bottom_bar = QHBoxLayout()
        self._folder_btn = QPushButton("📁 Выбрать папку вывода...")
        self._folder_btn.clicked.connect(self._choose_output_dir)
        self._folder_label = QLabel("Папка: рядом с исходными файлами")
        self._folder_label.setStyleSheet("color: #8B92B8; font-size: 11px;")
        self._overwrite_cb = QCheckBox("Перезаписать если существует")
        bottom_bar.addWidget(self._folder_btn)
        bottom_bar.addWidget(self._folder_label)
        bottom_bar.addStretch()
        bottom_bar.addWidget(self._overwrite_cb)
        layout.addLayout(bottom_bar)

        # --- Кнопки действий ---
        action_bar = QHBoxLayout()
        self._convert_btn = QPushButton("▶ Конвертировать всё")
        self._convert_btn.setEnabled(False)
        self._convert_btn.setFixedHeight(36)
        self._convert_btn.setStyleSheet(
            "QPushButton { background-color: #7C83FD; color: white; border-radius: 6px;"
            "  font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background-color: #9199FE; }"
            "QPushButton:disabled { background-color: #2E3250; color: #5C6380; }"
        )
        self._convert_btn.clicked.connect(self._start_conversion)

        self._cancel_btn = QPushButton("✕ Отмена")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setFixedHeight(36)
        self._cancel_btn.clicked.connect(self._cancel_conversion)

        action_bar.addWidget(self._convert_btn)
        action_bar.addWidget(self._cancel_btn)
        action_bar.addStretch()
        layout.addLayout(action_bar)

        self.statusBar().showMessage("Перетащите файлы или нажмите «Добавить файлы»")

    # ------------------------------------------------------------------
    # Слоты: управление файлами
    # ------------------------------------------------------------------

    def _on_files_dropped(self, paths: list[str]) -> None:
        self._task_queue.add_files(paths)

    def _on_add_files_clicked(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Выберите файлы для конвертации")
        if paths:
            self._task_queue.add_files(paths)

    def _on_clear_all(self) -> None:
        self._task_queue.clear_all()

    def _on_files_changed(self, count: int) -> None:
        self._files_count_label.setText(f"Файлов: {count}")
        self._convert_btn.setEnabled(count > 0)
        self._clear_btn.setEnabled(count > 0)

    def _choose_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
        if folder:
            self._output_dir = Path(folder)
            self._folder_label.setText(f"Папка: {folder}")

    # ------------------------------------------------------------------
    # Слоты: конвертация
    # ------------------------------------------------------------------

    def _start_conversion(self) -> None:
        cards = self._task_queue.cards()
        if not cards:
            return

        plan = ConversionPlan()
        self._job_card_map.clear()
        overwrite = self._overwrite_cb.isChecked()

        for card in cards:
            if not card.is_convertible():
                continue
            output_dir = self._output_dir or (card.file_path.parent / "converted")
            job = self._engine.build_job(
                file_path  = card.file_path,
                output_dir = output_dir,
                target_ext = card.target_ext,
                overwrite  = overwrite,
                params     = card.job_params,
            )
            if job:
                plan.jobs.append(job)
                self._job_card_map[job.id] = card.card_id
                card.set_status(JobStatus.PENDING)
                card.set_progress(0)

        if not plan.jobs:
            self.statusBar().showMessage("Нет файлов для конвертации (неподдерживаемые форматы?)")
            return

        self._cancel_flag[0] = False
        self._convert_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._task_queue.lock_all(True)
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

    # ------------------------------------------------------------------
    # Слоты: обновление карточек по job_id
    # ------------------------------------------------------------------

    def _get_card_by_job(self, job_id: str):
        card_id = self._job_card_map.get(job_id)
        return self._task_queue.get_card(card_id) if card_id else None

    def _on_job_started(self, job_id: str) -> None:
        if card := self._get_card_by_job(job_id):
            card.set_status(JobStatus.RUNNING)

    def _on_job_progress(self, job_id: str, percent: int) -> None:
        if card := self._get_card_by_job(job_id):
            card.set_progress(percent)

    def _on_job_finished(self, job_id: str) -> None:
        if card := self._get_card_by_job(job_id):
            card.set_progress(100)
            card.set_status(JobStatus.DONE)

    def _on_job_failed(self, job_id: str, error: str) -> None:
        if card := self._get_card_by_job(job_id):
            card.set_status(JobStatus.FAILED)
        self.statusBar().showMessage(f"Ошибка: {error[:120]}")

    def _on_all_done(self) -> None:
        self._convert_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._task_queue.lock_all(False)
        total  = len(self._job_card_map)
        done   = sum(
            1 for cid in self._job_card_map.values()
            if (c := self._task_queue.get_card(cid)) and c._status == JobStatus.DONE
        )
        failed = total - done
        msg = f"Готово: {done}/{total}"
        if failed:
            msg += f"  |  ❌ Ошибок: {failed}"
        self.statusBar().showMessage(msg)
