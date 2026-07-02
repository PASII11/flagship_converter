"""Qt-воркеры для выполнения конвертации в фоне."""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QRunnable, Signal

from flagship_converter.core.engine import ConversionEngine
from flagship_converter.core.models import ConversionPlan


class WorkerSignals(QObject):
    job_started = Signal(str)
    job_progress = Signal(str, int)    # job_id, percent
    job_finished = Signal(str)
    job_failed = Signal(str, str)
    job_cancelled = Signal(str)
    all_done = Signal()


class PlanRunner(QRunnable):
    def __init__(
        self,
        plan: ConversionPlan,
        engine: ConversionEngine,
        cancel_event: threading.Event,
    ) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self.plan = plan
        self.engine = engine
        self._cancel_event = cancel_event
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            self.engine.execute_plan(
                plan=self.plan,
                cancel_cb=self._cancel_event.is_set,
                on_job_started=self.signals.job_started.emit,
                on_job_finished=self.signals.job_finished.emit,
                on_job_failed=self.signals.job_failed.emit,
                on_job_cancelled=self.signals.job_cancelled.emit,
                on_job_progress=self.signals.job_progress.emit,
            )
        finally:
            self.signals.all_done.emit()
