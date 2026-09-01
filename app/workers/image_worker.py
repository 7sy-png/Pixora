"""Background worker for image processing."""

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.models import ProcessingOptions
from app.services import ImageService


class ImageWorkerSignals(QObject):
    """Deliver worker results back to the GUI thread."""

    finished = Signal(object, bytes)
    error = Signal(str)


class ImageWorker(QRunnable):
    """Run ImageService without blocking the Qt event loop."""

    def __init__(
        self,
        image_service: ImageService,
        image_path: str | Path,
        options: ProcessingOptions,
    ) -> None:
        super().__init__()
        self.image_service = image_service
        self.image_path = Path(image_path)
        self.options = options
        self.signals = ImageWorkerSignals()

    @Slot()
    def run(self) -> None:
        """Process the image and emit either a result or an error message."""
        result = None
        try:
            result = self.image_service.process(self.image_path, self.options)
            encoded_data = self.image_service.encode(result, self.options)
        except Exception as error:
            if result is not None:
                result.close()
            self.signals.error.emit(str(error))
            return

        self.signals.finished.emit(result, encoded_data)
