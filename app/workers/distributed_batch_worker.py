"""Qt workers for non-blocking communication with the distributed API."""

from pathlib import Path
from threading import Event
from time import sleep

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.models import ProcessingOptions
from app.services import DistributedClient


class DistributedBatchSignals(QObject):
    """Deliver remote batch progress back to the GUI thread."""

    submitted = Signal(object)
    progress = Signal(object)
    finished = Signal(object)
    cancelled = Signal()
    error = Signal(str)


class DistributedBatchWorker(QRunnable):
    """Submit and poll a remote batch without blocking Qt's event loop."""

    TERMINAL_STATES = frozenset({"SUCCESS", "FAILURE", "REVOKED"})

    def __init__(
        self,
        client: DistributedClient,
        image_paths: list[Path],
        options: ProcessingOptions,
        *,
        poll_interval_seconds: float = 0.5,
    ) -> None:
        super().__init__()
        self.client = client
        self.image_paths = image_paths
        self.options = options
        self.poll_interval_seconds = poll_interval_seconds
        self.signals = DistributedBatchSignals()
        self._cancelled = Event()
        self._cancel_remote = True
        self._batch_id: str | None = None

    def cancel(self, *, remote: bool = True) -> None:
        """Stop polling and optionally revoke unfinished server-side tasks."""
        self._cancel_remote = remote
        self._cancelled.set()

    @Slot()
    def run(self) -> None:
        """Submit the selected files and poll until every job is terminal."""
        try:
            self.client.check_health()
            created = self.client.submit_batch(self.image_paths, self.options)
            self.signals.submitted.emit(created)
            batch_id = str(created["batch_id"])
            self._batch_id = batch_id

            while not self._cancelled.is_set():
                status = self.client.get_batch_status(batch_id)
                self.signals.progress.emit(status)
                jobs = status.get("jobs", [])
                if jobs and all(
                    job.get("status") in self.TERMINAL_STATES for job in jobs
                ):
                    self.signals.finished.emit(status)
                    return
                sleep(self.poll_interval_seconds)
        except Exception as error:
            self.signals.error.emit(str(error))
            return

        if self._cancel_remote and self._batch_id is not None:
            try:
                status = self.client.cancel_batch(self._batch_id)
                self.signals.progress.emit(status)
            except Exception as error:
                self.signals.error.emit(str(error))
                return
        self.signals.cancelled.emit()


class DistributedDownloadSignals(QObject):
    """Report completion of a multi-result download."""

    finished = Signal(object)
    error = Signal(str)


class DistributedDownloadWorker(QRunnable):
    """Download every successful task result into a chosen directory."""

    def __init__(
        self,
        client: DistributedClient,
        jobs: list[dict[str, object]],
        destination: Path,
    ) -> None:
        super().__init__()
        self.client = client
        self.jobs = jobs
        self.destination = destination
        self.signals = DistributedDownloadSignals()

    @Slot()
    def run(self) -> None:
        """Download completed results and avoid overwriting existing files."""
        saved_paths: list[Path] = []
        try:
            for job in self.jobs:
                if job.get("status") != "SUCCESS":
                    continue
                output = job.get("output")
                if not isinstance(output, dict):
                    continue
                filename = str(output["filename"])
                destination = self._available_path(filename)
                saved_paths.append(
                    self.client.download_result(str(job["job_id"]), destination)
                )
        except Exception as error:
            self.signals.error.emit(str(error))
            return
        self.signals.finished.emit(saved_paths)

    def _available_path(self, filename: str) -> Path:
        """Return a unique path without altering an existing user file."""
        candidate = self.destination / filename
        suffix_number = 2
        while candidate.exists():
            candidate = self.destination / (
                f"{Path(filename).stem}_{suffix_number}{Path(filename).suffix}"
            )
            suffix_number += 1
        return candidate
