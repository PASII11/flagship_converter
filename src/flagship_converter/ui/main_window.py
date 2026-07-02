"""Main application window for Flagship File Converter."""
from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from flagship_converter.core.engine import ConversionEngine
from flagship_converter.core.models import ConversionPlan, JobStatus
from flagship_converter.ui import theme
from flagship_converter.ui.widgets.drop_zone import DropZone
from flagship_converter.ui.widgets.task_queue import TaskQueue
from flagship_converter.ui.workers import PlanRunner


def _shorten_middle(value: str, max_chars: int = 72) -> str:
    if len(value) <= max_chars:
        return value
    head = max_chars // 2 - 2
    tail = max_chars - head - 3
    return f"{value[:head]}...{value[-tail:]}"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Flagship File Converter")
        self.setMinimumSize(1180, 780)

        self._engine = ConversionEngine()
        self._output_dir: Path | None = None
        self._cancel_event: threading.Event | None = None
        self._is_converting = False
        self._active_runner: PlanRunner | None = None
        self._job_card_map: dict[str, str] = {}
        self._errors_by_job: dict[str, str] = {}
        self._progress_by_job: dict[str, int] = {}

        self._build_ui()
        self._connect_system_theme_listener()
        self._apply_theme()
        self._sync_file_controls()

    def _build_ui(self) -> None:
        self._root = QWidget()
        self._root.setObjectName("Root")
        self.setCentralWidget(self._root)

        shell = QHBoxLayout(self._root)
        shell.setContentsMargins(22, 22, 22, 18)
        shell.setSpacing(18)

        self._sidebar = self._build_sidebar()
        self._content = self._build_content()

        shell.addWidget(self._sidebar)
        shell.addWidget(self._content, stretch=1)

        self.statusBar().showMessage("Готов к работе.")

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(224)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        brand_mark = QLabel("F")
        brand_mark.setObjectName("BrandMark")
        brand_mark.setFixedSize(42, 42)
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._brand_title = QLabel("Flagship")
        self._brand_title.setObjectName("BrandTitle")
        self._brand_subtitle = QLabel("File Converter")
        self._brand_subtitle.setObjectName("BrandSubtitle")

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        brand_text.addWidget(self._brand_title)
        brand_text.addWidget(self._brand_subtitle)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        brand_row.addWidget(brand_mark)
        brand_row.addLayout(brand_text)
        layout.addLayout(brand_row)

        layout.addSpacing(10)

        self._nav_converter_btn = QPushButton("Конвертер")
        self._nav_queue_btn = QPushButton("Очередь")
        self._nav_settings_btn = QPushButton("Параметры")
        for button in (self._nav_converter_btn, self._nav_queue_btn, self._nav_settings_btn):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumHeight(38)

        layout.addWidget(self._nav_converter_btn)
        layout.addWidget(self._nav_queue_btn)
        layout.addWidget(self._nav_settings_btn)
        layout.addSpacing(14)

        self._sidebar_stat = QFrame()
        self._sidebar_stat.setObjectName("SidebarStat")
        stat_layout = QVBoxLayout(self._sidebar_stat)
        stat_layout.setContentsMargins(12, 12, 12, 12)
        stat_layout.setSpacing(8)

        self._sidebar_state_label = QLabel("Готово")
        self._sidebar_count_label = QLabel("0 файлов")
        self._sidebar_hint_label = QLabel("Добавьте файлы для конвертации.")
        self._sidebar_hint_label.setWordWrap(True)

        stat_layout.addWidget(self._sidebar_state_label)
        stat_layout.addWidget(self._sidebar_count_label)
        stat_layout.addWidget(self._sidebar_hint_label)
        layout.addWidget(self._sidebar_stat)

        layout.addStretch()

        self._theme_caption = QLabel("Тема")
        self._theme_box = QComboBox()
        self._theme_box.addItem("Система", theme.ThemeMode.SYSTEM.value)
        self._theme_box.addItem("Светлая", theme.ThemeMode.LIGHT.value)
        self._theme_box.addItem("Темная", theme.ThemeMode.DARK.value)
        self._theme_box.currentIndexChanged.connect(self._on_theme_changed)

        layout.addWidget(self._theme_caption)
        layout.addWidget(self._theme_box)

        return sidebar

    def _build_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self._top_bar = self._build_top_bar()
        self._main_panel = self._build_conversion_panel()
        self._status_panel = self._build_status_panel()

        layout.addWidget(self._top_bar)

        workspace = QHBoxLayout()
        workspace.setSpacing(16)
        workspace.addWidget(self._main_panel, stretch=3)
        workspace.addWidget(self._status_panel, stretch=1)
        layout.addLayout(workspace, stretch=1)

        return content

    def _build_top_bar(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("TopBar")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self._title_label = QLabel("Конвертация файлов")
        self._subtitle_label = QLabel(
            "Локальная обработка изображений, аудио, видео и документов"
        )
        title_col.addWidget(self._title_label)
        title_col.addWidget(self._subtitle_label)
        layout.addLayout(title_col, stretch=1)

        self._state_label = QLabel()
        self._state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._state_label.setMinimumWidth(128)
        layout.addWidget(self._state_label)

        self._files_count_label = QLabel()
        self._files_count_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._files_count_label.setMinimumWidth(170)
        layout.addWidget(self._files_count_label)

        return panel

    def _build_conversion_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("MainPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)

        self._drop_zone = DropZone()
        self._drop_zone.files_dropped.connect(self._on_files_dropped)
        self._drop_zone.clicked.connect(self._on_add_files_clicked)
        layout.addWidget(self._drop_zone)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self._add_btn = QPushButton("Добавить файлы")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._on_add_files_clicked)

        self._clear_btn = QPushButton("Очистить очередь")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.clicked.connect(self._on_clear_all)
        self._clear_btn.setEnabled(False)

        toolbar.addWidget(self._add_btn)
        toolbar.addWidget(self._clear_btn)
        toolbar.addStretch()

        self._summary_label = QLabel()
        self._summary_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._summary_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        toolbar.addWidget(self._summary_label)
        layout.addLayout(toolbar)

        queue_header = QHBoxLayout()
        queue_header.setSpacing(12)
        self._queue_title = QLabel("Очередь")
        self._queue_subtitle = QLabel("Формат и параметры настраиваются отдельно.")
        queue_title_col = QVBoxLayout()
        queue_title_col.setSpacing(2)
        queue_title_col.addWidget(self._queue_title)
        queue_title_col.addWidget(self._queue_subtitle)
        queue_header.addLayout(queue_title_col, stretch=1)

        self._overall_progress_label = QLabel("Общий прогресс: 0%")
        self._overall_progress_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        queue_header.addWidget(self._overall_progress_label)
        layout.addLayout(queue_header)

        self._overall_progress = QProgressBar()
        self._overall_progress.setRange(0, 100)
        self._overall_progress.setValue(0)
        self._overall_progress.setTextVisible(False)
        self._overall_progress.setFixedHeight(6)
        layout.addWidget(self._overall_progress)

        self._task_queue = TaskQueue()
        self._task_queue.files_changed.connect(self._on_files_changed)
        layout.addWidget(self._task_queue, stretch=1)

        return panel

    def _build_status_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("StatusPanel")
        panel.setMinimumWidth(300)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        self._status_panel_title = QLabel("Статус")
        self._status_panel_subtitle = QLabel("Сводка текущей очереди")
        layout.addWidget(self._status_panel_title)
        layout.addWidget(self._status_panel_subtitle)

        self._metric_ready = self._build_metric_card("К обработке", "0")
        self._metric_done = self._build_metric_card("Готово", "0")
        self._metric_failed = self._build_metric_card("Ошибки", "0")
        layout.addWidget(self._metric_ready)
        layout.addWidget(self._metric_done)
        layout.addWidget(self._metric_failed)

        self._output_panel = QFrame()
        self._output_panel.setObjectName("InnerPanel")
        output_layout = QVBoxLayout(self._output_panel)
        output_layout.setContentsMargins(12, 12, 12, 12)
        output_layout.setSpacing(10)

        self._output_title = QLabel("Папка вывода")
        self._folder_label = QLabel("Подпапка converted рядом с исходником")
        self._folder_label.setWordWrap(True)

        self._folder_btn = QPushButton("Выбрать папку")
        self._folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._folder_btn.clicked.connect(self._choose_output_dir)

        self._overwrite_cb = QCheckBox("Перезаписывать существующие")
        self._overwrite_cb.setCursor(Qt.CursorShape.PointingHandCursor)

        output_layout.addWidget(self._output_title)
        output_layout.addWidget(self._folder_label)
        output_layout.addWidget(self._folder_btn)
        output_layout.addWidget(self._overwrite_cb)
        layout.addWidget(self._output_panel)

        layout.addStretch()

        self._cancel_btn = QPushButton("Отменить")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel_conversion)

        self._convert_btn = QPushButton("Конвертировать")
        self._convert_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._convert_btn.setEnabled(False)
        self._convert_btn.setMinimumHeight(42)
        self._convert_btn.clicked.connect(self._start_conversion)

        layout.addWidget(self._cancel_btn)
        layout.addWidget(self._convert_btn)

        return panel

    def _build_metric_card(self, title: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("MetricCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("MetricTitle")
        value_label = QLabel(value)
        value_label.setObjectName("MetricValue")
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(title_label, stretch=1)
        layout.addWidget(value_label)
        card._title_label = title_label  # type: ignore[attr-defined]
        card._value_label = value_label  # type: ignore[attr-defined]
        return card

    def _connect_system_theme_listener(self) -> None:
        qapp = QApplication.instance()
        if qapp is None:
            return
        style_hints = qapp.styleHints()
        signal = getattr(style_hints, "colorSchemeChanged", None)
        if signal is not None:
            signal.connect(lambda _scheme: self._apply_theme_if_system())

    def _on_theme_changed(self, *_args: object) -> None:
        mode = self._theme_box.currentData()
        theme.set_theme_mode(mode)
        self._apply_theme()

    def _apply_theme_if_system(self) -> None:
        if theme.theme_mode() == theme.ThemeMode.SYSTEM:
            self._apply_theme()

    def _apply_theme(self) -> None:
        p = theme.palette()
        self.setStyleSheet(theme.app_qss(p))
        self._root.setStyleSheet(theme.root_qss(p))

        self._sidebar.setStyleSheet(theme.sidebar_qss(p))
        self._content.setStyleSheet("background: transparent;")
        self._nav_converter_btn.setStyleSheet(theme.nav_item_qss(True, p))
        self._nav_queue_btn.setStyleSheet(theme.nav_item_qss(False, p))
        self._nav_settings_btn.setStyleSheet(theme.nav_item_qss(False, p))

        for panel in (self._top_bar, self._main_panel, self._status_panel):
            panel.setStyleSheet(theme.panel_qss(panel.objectName(), p, radius=20))
            panel.setGraphicsEffect(theme.make_shadow(p))

        self._sidebar_stat.setStyleSheet(theme.panel_qss("SidebarStat", p, radius=16))
        self._output_panel.setStyleSheet(theme.panel_qss("InnerPanel", p, radius=16))

        for metric in (self._metric_ready, self._metric_done, self._metric_failed):
            metric.setStyleSheet(theme.panel_qss("MetricCard", p, radius=14))
            metric._title_label.setStyleSheet(theme.text_style(p.text_secondary, 12, 600))
            metric._value_label.setStyleSheet(theme.text_style(p.text_primary, 20, 780))

        self._theme_box.setStyleSheet(theme.input_qss(p))
        self._add_btn.setStyleSheet(theme.secondary_button_qss(p))
        self._clear_btn.setStyleSheet(theme.ghost_button_qss(p))
        self._folder_btn.setStyleSheet(theme.secondary_button_qss(p))
        self._cancel_btn.setStyleSheet(theme.ghost_button_qss(p, danger=True))
        self._convert_btn.setStyleSheet(theme.primary_button_qss(p))
        self._overwrite_cb.setStyleSheet(theme.checkbox_qss(p))
        self._overall_progress.setStyleSheet(theme.progress_qss(p.accent, p))

        self._style_static_labels(p)
        self._drop_zone.apply_theme(p)
        self._task_queue.apply_theme(p)
        self._style_state()
        self._style_message()

    def _style_static_labels(self, p: theme.Palette) -> None:
        self._title_label.setStyleSheet(theme.text_style(p.text_primary, 24, 820))
        self._subtitle_label.setStyleSheet(theme.text_style(p.text_secondary, 13, 500))
        self._files_count_label.setStyleSheet(theme.text_style(p.text_secondary, 13, 700))
        self._queue_title.setStyleSheet(theme.text_style(p.text_primary, 16, 800))
        self._queue_subtitle.setStyleSheet(theme.text_style(p.text_secondary, 12, 500))
        self._overall_progress_label.setStyleSheet(theme.text_style(p.text_secondary, 12, 700))
        self._status_panel_title.setStyleSheet(theme.text_style(p.text_primary, 18, 800))
        self._status_panel_subtitle.setStyleSheet(theme.text_style(p.text_secondary, 12, 500))
        self._output_title.setStyleSheet(theme.text_style(p.text_primary, 13, 800))
        self._folder_label.setStyleSheet(theme.text_style(p.text_secondary, 12, 500))
        self._theme_caption.setStyleSheet(theme.text_style(p.text_secondary, 12, 700))
        self._sidebar_state_label.setStyleSheet(theme.text_style(p.text_primary, 14, 780))
        self._sidebar_count_label.setStyleSheet(theme.text_style(p.accent, 24, 820))
        self._sidebar_hint_label.setStyleSheet(theme.text_style(p.text_secondary, 12, 500))
        self._summary_label.setStyleSheet(theme.text_style(p.text_secondary, 13, 650))
        self._brand_mark_style(p)
        self._brand_title.setStyleSheet(theme.text_style(p.text_primary, 18, 840))
        self._brand_subtitle.setStyleSheet(theme.text_style(p.text_secondary, 12, 560))

    def _brand_mark_style(self, p: theme.Palette) -> None:
        self.findChild(QLabel, "BrandMark").setStyleSheet(
            "QLabel#BrandMark {"
            f"color: #FFFFFF; background-color: {p.accent};"
            f"border: 1px solid {p.accent_pressed};"
            "border-radius: 13px; font-size: 18px; font-weight: 840;"
            "}"
        )

    def _on_files_dropped(self, paths: list[str]) -> None:
        if self._is_converting:
            return
        self._add_files(paths)

    def _on_add_files_clicked(self) -> None:
        if self._is_converting:
            return
        paths, _ = QFileDialog.getOpenFileNames(self, "Выберите файлы для конвертации")
        if paths:
            self._add_files(paths)

    def _add_files(self, paths: list[str]) -> None:
        added = self._task_queue.add_files(paths)
        self._sync_file_controls(update_message=False)
        if added:
            self._set_message(f"Добавлено файлов: {added}.", "ready")
        else:
            self._set_message("Новые файлы не добавлены: проверьте путь или дубликаты.", "warning")

    def _on_clear_all(self) -> None:
        if self._is_converting:
            return
        self._task_queue.clear_all()
        self._job_card_map.clear()
        self._errors_by_job.clear()
        self._progress_by_job.clear()
        self._set_overall_progress(0)
        self._sync_file_controls()

    def _on_files_changed(self, count: int) -> None:
        self._sync_file_controls()

    def _choose_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
        if folder:
            self._output_dir = Path(folder)
            display_path = _shorten_middle(folder, 74)
            self._folder_label.setText(f"Сохранять в: {display_path}")
            self._folder_label.setToolTip(folder)
            self._set_message("Папка вывода обновлена.", "ready")

    def _start_conversion(self) -> None:
        if self._is_converting:
            return

        cards = self._task_queue.cards()
        if not cards:
            self._set_message("Добавьте файлы перед запуском конвертации.", "warning")
            return

        plan = ConversionPlan()
        self._job_card_map.clear()
        self._errors_by_job.clear()
        self._progress_by_job.clear()
        overwrite = self._overwrite_cb.isChecked()
        reserved_outputs: set[Path] = set()

        for card in cards:
            if not card.is_convertible():
                continue
            output_dir = self._output_dir or (card.file_path.parent / "converted")
            job = self._engine.build_job(
                file_path=card.file_path,
                output_dir=output_dir,
                target_ext=card.target_ext,
                overwrite=overwrite,
                params=card.job_params,
                reserved_outputs=reserved_outputs,
            )
            if job:
                plan.jobs.append(job)
                self._job_card_map[job.id] = card.card_id
                self._progress_by_job[job.id] = 0
                card.set_output_path(job.output_path)
                card.set_status(JobStatus.PENDING)
                card.set_progress(0)
            else:
                card.set_error("Выбранный формат недоступен для этого файла.")

        if not plan.jobs:
            self._set_state("Нет задач", "warning")
            self._set_message("Нет поддерживаемых файлов для конвертации.", "warning")
            return

        self._cancel_event = threading.Event()
        self._set_overall_progress(0)
        self._set_conversion_controls(True)
        self._set_state("Конвертация", "running")
        self._set_message(f"Конвертация запущена. Задач в плане: {plan.total}.", "running")

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
        self._cancel_btn.setEnabled(False)
        self._set_state("Отмена", "warning")
        self._set_message(
            "Останавливаю текущие задачи. Уже завершённые файлы останутся на месте.",
            "warning",
        )

    def _set_conversion_controls(self, converting: bool) -> None:
        self._is_converting = converting
        has_convertible = self._task_queue.has_convertible_files()
        self._add_btn.setEnabled(not converting)
        self._drop_zone.setEnabled(not converting)
        self._folder_btn.setEnabled(not converting)
        self._overwrite_cb.setEnabled(not converting)
        self._convert_btn.setEnabled((not converting) and has_convertible)
        self._clear_btn.setEnabled((not converting) and self._task_queue.count() > 0)
        self._cancel_btn.setEnabled(converting)
        self._task_queue.lock_all(converting)
        if not converting:
            self._sync_file_controls(update_message=False)

    def _get_card_by_job(self, job_id: str):
        card_id = self._job_card_map.get(job_id)
        return self._task_queue.get_card(card_id) if card_id else None

    def _on_job_started(self, job_id: str) -> None:
        self._progress_by_job[job_id] = max(self._progress_by_job.get(job_id, 0), 1)
        if card := self._get_card_by_job(job_id):
            card.set_status(JobStatus.RUNNING)
        self._update_overall_progress()

    def _on_job_progress(self, job_id: str, percent: int) -> None:
        self._progress_by_job[job_id] = max(0, min(percent, 100))
        if card := self._get_card_by_job(job_id):
            card.set_progress(percent)
        self._update_overall_progress()

    def _on_job_finished(self, job_id: str) -> None:
        self._progress_by_job[job_id] = 100
        if card := self._get_card_by_job(job_id):
            card.set_progress(100)
            card.set_status(JobStatus.DONE)
        self._update_overall_progress()

    def _on_job_failed(self, job_id: str, error: str) -> None:
        self._errors_by_job[job_id] = error
        self._progress_by_job[job_id] = 100
        if card := self._get_card_by_job(job_id):
            card.set_progress(100)
            card.set_error(error)
        self._set_message(f"Ошибка конвертации: {error[:140]}", "danger")
        self._update_overall_progress()

    def _on_job_cancelled(self, job_id: str) -> None:
        self._progress_by_job[job_id] = 100
        if card := self._get_card_by_job(job_id):
            card.set_status(JobStatus.CANCELLED)
        self._update_overall_progress()

    def _on_all_done(self) -> None:
        self._set_conversion_controls(False)
        self._active_runner = None
        self._cancel_event = None

        total = len(self._job_card_map)
        statuses = [
            card.status
            for card_id in self._job_card_map.values()
            if (card := self._task_queue.get_card(card_id))
        ]
        done = sum(1 for status in statuses if status == JobStatus.DONE)
        failed = sum(1 for status in statuses if status == JobStatus.FAILED)
        cancelled = sum(1 for status in statuses if status == JobStatus.CANCELLED)

        if total == 0:
            self._set_state("Готово", "idle")
            self._set_message("Готов к работе.", "idle")
        elif cancelled and done == 0 and failed == 0:
            self._set_state("Отменено", "warning")
            self._set_message(
                f"Конвертация отменена. Отменено задач: {cancelled} из {total}.",
                "warning",
            )
        elif failed == total:
            last_error = next(reversed(self._errors_by_job.values()), "Неизвестная ошибка")
            self._set_state("Ошибка", "danger")
            self._set_message(
                f"Все задачи завершились ошибкой. Последняя ошибка: {last_error[:140]}",
                "danger",
            )
        elif failed or cancelled:
            parts = [f"успешно: {done} из {total}"]
            if failed:
                parts.append(f"ошибок: {failed}")
            if cancelled:
                parts.append(f"отменено: {cancelled}")
            self._set_state("С ошибками", "warning")
            self._set_message("Завершено, " + ", ".join(parts) + ".", "warning")
        else:
            self._set_state("Завершено", "success")
            self._set_message(f"Конвертация завершена. Успешно: {done} из {total}.", "success")

        if total:
            self._set_overall_progress(100)

    def _sync_file_controls(self, update_message: bool = True) -> None:
        count = self._task_queue.count()
        convertible = self._task_queue.convertible_count()
        statuses = [card.status for card in self._task_queue.cards()]
        done = sum(1 for status in statuses if status == JobStatus.DONE)
        failed = sum(1 for status in statuses if status == JobStatus.FAILED)

        if count == 0:
            count_text = "0 файлов"
        elif convertible == count:
            count_text = f"{count} файлов"
        else:
            count_text = f"{count} файлов / {convertible} поддерживается"

        self._files_count_label.setText(count_text)
        self._sidebar_count_label.setText(str(count))
        self._metric_ready._value_label.setText(str(convertible))  # type: ignore[attr-defined]
        self._metric_done._value_label.setText(str(done))  # type: ignore[attr-defined]
        self._metric_failed._value_label.setText(str(failed))  # type: ignore[attr-defined]

        self._clear_btn.setEnabled(count > 0 and not self._is_converting)
        self._convert_btn.setEnabled(convertible > 0 and not self._is_converting)
        self._convert_btn.setText(
            "Конвертировать" if convertible <= 1 else f"Конвертировать {convertible}"
        )

        if self._is_converting or not update_message:
            return

        if count == 0:
            self._set_state("Готово", "idle")
            self._set_message("Добавьте файлы или перетащите их в рабочую область.", "idle")
        elif convertible == 0:
            self._set_state("Нет задач", "warning")
            self._set_message("В очереди нет файлов с поддерживаемым форматом.", "warning")
        else:
            self._set_state("Готово", "ready")
            self._set_message(f"Готово к конвертации: {convertible} файлов.", "ready")

    def _set_state(self, text: str, tone: str) -> None:
        self._state_text = text
        self._state_tone = tone
        self._style_state()

    def _style_state(self) -> None:
        p = theme.palette()
        tone = getattr(self, "_state_tone", "idle")
        text = getattr(self, "_state_text", "Готово")
        palette = {
            "idle": (p.text_secondary, p.surface_secondary, p.border),
            "ready": (p.accent, p.accent_soft, p.border),
            "running": (p.accent, p.accent_soft, p.border),
            "success": (p.green, p.green_soft, p.border),
            "warning": (p.orange, p.orange_soft, p.border),
            "danger": (p.error, p.error_soft, p.border),
        }
        fg, bg, border = palette.get(tone, palette["idle"])
        self._state_label.setText(text)
        self._state_label.setStyleSheet(theme.status_pill_style(fg, bg, border))
        self._sidebar_state_label.setText(text)

    def _set_message(self, message: str, tone: str) -> None:
        self._message_text = message
        self._message_tone = tone
        self._style_message()
        self.statusBar().showMessage(message)

    def _style_message(self) -> None:
        p = theme.palette()
        tone = getattr(self, "_message_tone", "idle")
        message = getattr(self, "_message_text", "Добавьте файлы для конвертации.")
        color = {
            "ready": p.accent,
            "running": p.accent,
            "success": p.green,
            "warning": p.orange,
            "danger": p.error,
        }.get(tone, p.text_secondary)
        self._summary_label.setText(message)
        self._summary_label.setStyleSheet(theme.text_style(color, 13, 700))
        self._sidebar_hint_label.setText(message)
        self._sidebar_hint_label.setStyleSheet(theme.text_style(p.text_secondary, 12, 500))

    def _set_overall_progress(self, percent: int) -> None:
        safe_percent = max(0, min(percent, 100))
        self._overall_progress.setValue(safe_percent)
        self._overall_progress_label.setText(f"Общий прогресс: {safe_percent}%")

    def _update_overall_progress(self) -> None:
        if not self._progress_by_job:
            self._set_overall_progress(0)
            return
        percent = round(sum(self._progress_by_job.values()) / len(self._progress_by_job))
        self._set_overall_progress(percent)
