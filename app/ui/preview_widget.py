"""Image preview widget."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QPixmap, QResizeEvent, QTransform
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from app.models import ImageInfo
from app.ui.drop_zone import DropZoneWidget
from app.utils.file_utils import format_file_size
from app.utils.validation import ImageValidationError, validate_image_file


class PreviewWidget(QWidget):
    """Switch between the drop zone and a scaled image preview."""

    MAX_RENDER_DIMENSION = 2048
    file_selected = Signal(str)
    file_rejected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("previewWidget")

        self._source_pixmap = QPixmap()
        self._image_info: ImageInfo | None = None
        self._output_width: int | None = None
        self._output_height: int | None = None
        self._rotation = 0
        self._flip_horizontal = False
        self._flip_vertical = False

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
        return self._image_info.path if self._image_info is not None else None

    @property
    def image_info(self) -> ImageInfo | None:
        """Return metadata for the image currently shown in preview."""
        return self._image_info

    @Slot(str)
    def load_image(self, file_path: str) -> None:
        """Load an image and switch from the drop zone to preview mode."""
        try:
            validated_path = validate_image_file(file_path)
        except ImageValidationError as error:
            self.file_rejected.emit(str(error))
            return

        source_pixmap = QPixmap(str(validated_path))
        if source_pixmap.isNull():
            self.file_rejected.emit("Не удалось открыть изображение")
            return

        resolved_path = validated_path.resolve()
        suffix = resolved_path.suffix.lower()
        format_name = "JPEG" if suffix in {".jpg", ".jpeg"} else suffix[1:].upper()

        self._source_pixmap = source_pixmap
        self._output_width = source_pixmap.width()
        self._output_height = source_pixmap.height()
        self._rotation = 0
        self._flip_horizontal = False
        self._flip_vertical = False
        self._image_info = ImageInfo(
            path=resolved_path,
            filename=resolved_path.name,
            format=format_name,
            width=source_pixmap.width(),
            height=source_pixmap.height(),
            size=resolved_path.stat().st_size,
        )
        self._update_file_info()
        self._stack.setCurrentWidget(self._preview_page)
        self._update_scaled_pixmap()
        self.file_selected.emit(str(resolved_path))

    @Slot(int, bool, bool)
    def set_transform(
        self,
        rotation: int,
        flip_horizontal: bool,
        flip_vertical: bool,
    ) -> None:
        """Preview rotation and reflection without changing the source file."""
        self._rotation = rotation
        self._flip_horizontal = flip_horizontal
        self._flip_vertical = flip_vertical
        self._update_scaled_pixmap()

    @Slot(int, int)
    def set_output_size(self, width: int, height: int) -> None:
        """Preview the exact output proportions without editing the source."""
        if width < 1 or height < 1:
            return
        self._output_width = width
        self._output_height = height
        self._update_scaled_pixmap()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Rescale the preview whenever the available area changes."""
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def _update_scaled_pixmap(self) -> None:
        """Fit the source image into the label without changing its ratio."""
        if self._source_pixmap.isNull():
            return

        preview_pixmap = self._transformed_pixmap()
        scaled_pixmap = preview_pixmap.scaled(
            self._preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview_label.setPixmap(scaled_pixmap)

    def _transformed_pixmap(self) -> QPixmap:
        """Apply the same visual transform order as the processing pipeline."""
        pixmap = self._resized_pixmap()
        if self._rotation:
            pixmap = pixmap.transformed(
                QTransform().rotate(self._rotation),
                Qt.TransformationMode.FastTransformation,
            )
        if self._flip_horizontal or self._flip_vertical:
            pixmap = pixmap.transformed(
                QTransform().scale(
                    -1 if self._flip_horizontal else 1,
                    -1 if self._flip_vertical else 1,
                ),
                Qt.TransformationMode.FastTransformation,
            )
        return pixmap

    def _resized_pixmap(self) -> QPixmap:
        """Render output proportions while keeping preview memory bounded."""
        if self._output_width is None or self._output_height is None:
            return self._source_pixmap

        largest_dimension = max(self._output_width, self._output_height)
        scale = min(1.0, self.MAX_RENDER_DIMENSION / largest_dimension)
        render_width = max(1, round(self._output_width * scale))
        render_height = max(1, round(self._output_height * scale))
        if (
            render_width == self._source_pixmap.width()
            and render_height == self._source_pixmap.height()
        ):
            return self._source_pixmap

        return self._source_pixmap.scaled(
            render_width,
            render_height,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _create_file_info_bar(self, parent: QWidget) -> QFrame:
        """Create labels for the selected file metadata."""
        info_bar = QFrame(parent)
        info_bar.setObjectName("fileInfoBar")

        layout = QVBoxLayout(info_bar)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(6)

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(12)

        self._file_name_label = QLabel(info_bar)
        self._file_name_label.setObjectName("fileName")
        title_layout.addWidget(self._file_name_label, stretch=1)

        choose_another_button = QPushButton("Другое изображение", info_bar)
        choose_another_button.setObjectName("compactButton")
        choose_another_button.setCursor(Qt.CursorShape.PointingHandCursor)
        choose_another_button.setToolTip("Выбрать новый исходный файл")
        choose_another_button.clicked.connect(self.drop_zone.open_file_dialog)
        title_layout.addWidget(choose_another_button)
        layout.addLayout(title_layout)

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
        if self._image_info is None:
            return

        self._file_name_label.setText(self._image_info.filename)
        self._file_name_label.setToolTip(str(self._image_info.path))
        self._file_format_label.setText(self._image_info.format)
        self._file_resolution_label.setText(
            f"{self._image_info.width} × {self._image_info.height}"
        )
        self._file_size_label.setText(format_file_size(self._image_info.size))
