"""Image preview widget."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel, QSizePolicy, QStackedLayout, QWidget

from app.ui.drop_zone import DropZoneWidget


class PreviewWidget(QWidget):
    """Switch between the drop zone and a scaled image preview."""

    file_selected = Signal(str)
    file_rejected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("previewWidget")

        self._source_pixmap = QPixmap()
        self._current_file_path: Path | None = None

        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)

        self.drop_zone = DropZoneWidget(self)
        self.drop_zone.file_selected.connect(self.load_image)
        self.drop_zone.file_rejected.connect(self.file_rejected)
        self._stack.addWidget(self.drop_zone)

        self._preview_label = QLabel(self)
        self._preview_label.setObjectName("previewImage")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored,
        )
        self._stack.addWidget(self._preview_label)

    @property
    def current_file_path(self) -> Path | None:
        """Return the path of the image currently shown in preview."""
        return self._current_file_path

    @Slot(str)
    def load_image(self, file_path: str) -> None:
        """Load an image and switch from the drop zone to preview mode."""
        source_pixmap = QPixmap(file_path)
        if source_pixmap.isNull():
            self.file_rejected.emit("Не удалось открыть изображение")
            return

        self._source_pixmap = source_pixmap
        self._current_file_path = Path(file_path)
        self._stack.setCurrentWidget(self._preview_label)
        self._update_scaled_pixmap()
        self.file_selected.emit(str(self._current_file_path.resolve()))

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Rescale the preview whenever the available area changes."""
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def _update_scaled_pixmap(self) -> None:
        """Fit the source image into the label without changing its ratio."""
        if self._source_pixmap.isNull():
            return

        target_size = self._preview_label.size().boundedTo(
            self._source_pixmap.size()
        )
        scaled_pixmap = self._source_pixmap.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview_label.setPixmap(scaled_pixmap)
