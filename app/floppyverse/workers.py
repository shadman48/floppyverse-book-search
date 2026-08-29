from __future__ import annotations

import traceback

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    succeeded = Signal(str, list)
    failed = Signal(str, str)
    finished = Signal(str)


class SearchWorker(QRunnable):
    def __init__(self, source, query: str):
        super().__init__()
        self.source = source
        self.query = query
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.succeeded.emit(self.source.name, self.source.search(self.query))
        except Exception as exc:
            traceback.print_exc()
            self.signals.failed.emit(self.source.name, str(exc))
        finally:
            self.signals.finished.emit(self.source.name)

