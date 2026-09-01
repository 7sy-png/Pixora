"""Tests for the background image worker."""

import threading

from PIL import Image
from PySide6.QtCore import QCoreApplication, QEventLoop, QThreadPool, QTimer

from app.models import ProcessingOptions
from app.workers import ImageWorker


class RecordingImageService:
    """Minimal service double that records its execution thread."""

    def __init__(self) -> None:
        self.thread_id: int | None = None

    def process(self, _image_path, options: ProcessingOptions) -> Image.Image:
        self.thread_id = threading.get_ident()
        return Image.new("RGB", (options.width, options.height))


def test_image_worker_runs_on_thread_pool() -> None:
    application = QCoreApplication.instance() or QCoreApplication([])
    service = RecordingImageService()
    worker = ImageWorker(service, "unused.png", ProcessingOptions(4, 3))
    results: list[Image.Image] = []

    event_loop = QEventLoop()
    worker.signals.finished.connect(results.append)
    worker.signals.finished.connect(event_loop.quit)

    pool = QThreadPool()
    pool.start(worker)
    QTimer.singleShot(3000, event_loop.quit)
    event_loop.exec()
    pool.waitForDone()

    assert application is not None
    assert service.thread_id is not None
    assert service.thread_id != threading.get_ident()
    assert len(results) == 1
    assert results[0].size == (4, 3)
    results[0].close()


def test_image_worker_emits_error_message() -> None:
    class FailingService:
        def process(self, _image_path, _options):
            raise ValueError("processing failed")

    worker = ImageWorker(FailingService(), "unused.png", ProcessingOptions(1, 1))
    errors: list[str] = []
    worker.signals.error.connect(errors.append)

    worker.run()

    assert errors == ["processing failed"]
