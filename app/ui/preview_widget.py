"""Image preview widget."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from app.ui.drop_zone import DropZoneWidget
from app.utils.file_utils import format_file_size


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

        preview_page = QWidget(self)
        preview_page.setObjectName("previewPage")
        preview_layout = QVBoxLayout(preview_page)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(14)

        self._preview_label = QLabel(preview_page)
        self._preview_label.setObjectName("previewImage")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored,
        )
        preview_layout.addWidget(self._preview_label, stretch=1)

        preview_layout.addWidget(self._create_file_info_bar(preview_page))
        self._stack.addWidget(preview_page)
        self._preview_page = preview_page

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
        self._update_file_info()
        self._stack.setCurrentWidget(self._preview_page)
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

    def _create_file_info_bar(self, parent: QWidget) -> QFrame:
        """Create labels for the selected file metadata."""
        info_bar = QFrame(parent)
        info_bar.setObjectName("fileInfoBar")

        layout = QVBoxLayout(info_bar)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(6)

        self._file_name_label = QLabel(info_bar)
        self._file_name_label.setObjectName("fileName")
        layout.addWidget(self._file_name_label)

        details_layout = QHBoxLayout()
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(12)

        self._file_format_label = QLabel(info_bar)
        self._file_format_label.setObjectName("fileDetail")
        details_layout.addWidget(self._file_format_label)

        self._file_resolution_label = QLabel(info_bar)
        self._file_resolution_label.setObjectName("fileDetail")
        details_layout.addWidget(self._file_resolution_label)

        self._file_size_label = QLabel(info_bar)
        self._file_size_label.setObjectName("fileDetail")
        details_layout.addWidget(self._file_size_label)
        details_layout.addStretch()

        layout.addLayout(details_layout)
        return info_bar

    def _update_file_info(self) -> None:
        """Fill the metadata labels for the current source image."""
        if self._current_file_path is None:
            return

        suffix = self._current_file_path.suffix.lower()
        format_name = "JPEG" if suffix in {".jpg", ".jpeg"} else suffix[1:].upper()

        self._file_name_label.setText(self._current_file_path.name)
        self._file_name_label.setToolTip(str(self._current_file_path))
        self._file_format_label.setText(format_name)
        self._file_resolution_label.setText(
            f"{self._source_pixmap.width()} × {self._source_pixmap.height()}"
        )
        self._file_size_label.setText(
            format_file_size(self._current_file_path.stat().st_size)
        )
