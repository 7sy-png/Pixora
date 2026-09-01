"""Drag-and-drop area for selecting an image."""

from pathlib import Path

from PySide6.QtCore import QMimeData, Qt, Signal, Slot
from PySide6.QtGui import (
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.utils.validation import (
    ImageValidationError,
    SUPPORTED_IMAGE_EXTENSIONS,
    validate_image_file,
)


class DropZoneWidget(QWidget):
    """Accept supported local image files dropped by the user."""

    SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS
    IMAGE_FILTER = "Изображения (*.jpg *.jpeg *.png *.webp)"
    DEFAULT_TITLE = "Перетащите изображение сюда"
    ACTIVE_TITLE = "Отпустите файл здесь"

    file_selected = Signal(str)
    file_rejected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setProperty("dragActive", False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel("＋", self)
        icon_label.setObjectName("dropIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        self._title_label = QLabel(self.DEFAULT_TITLE, self)
        self._title_label.setObjectName("dropTitle")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title_label)

        or_label = QLabel("или", self)
        or_label.setObjectName("dropOrLabel")
        or_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(or_label)

        self.choose_file_button = QPushButton("Выбрать изображение", self)
        self.choose_file_button.setObjectName("chooseFileButton")
        self.choose_file_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.choose_file_button.clicked.connect(self.open_file_dialog)
        layout.addWidget(
            self.choose_file_button,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )

        hint_label = QLabel("JPG · PNG · WEBP · до 20 МБ", self)
        hint_label.setObjectName("dropHint")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint_label)

    @classmethod
    def supported_file_from_mime_data(cls, mime_data: QMimeData) -> Path | None:
        """Return the first supported local image from MIME data."""
        file_path = cls.local_file_from_mime_data(mime_data)
        if file_path is not None and cls.is_supported_file(file_path):
            return file_path
        return None

    @staticmethod
    def local_file_from_mime_data(mime_data: QMimeData) -> Path | None:
        """Return the first local file path regardless of image validity."""
        if not mime_data.hasUrls():
            return None
        for url in mime_data.urls():
            if url.isLocalFile():
                return Path(url.toLocalFile())
        return None

    @classmethod
    def is_supported_file(cls, file_path: Path) -> bool:
        """Check that a path is an existing image with a supported extension."""
        try:
            validate_image_file(file_path, verify_content=False)
        except ImageValidationError:
            return False
        return True

    @Slot()
    def open_file_dialog(self) -> None:
        """Open a native file picker and emit the selected image path."""
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите изображение",
            "",
            self.IMAGE_FILTER,
        )
        if not selected_path:
            return

        file_path = Path(selected_path)
        try:
            validate_image_file(file_path, verify_content=False)
        except ImageValidationError as error:
            self.file_rejected.emit(str(error))
            return

        self.file_selected.emit(str(file_path.resolve()))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept a drag when it contains a supported local image."""
        if self.supported_file_from_mime_data(event.mimeData()) is not None:
            event.acceptProposedAction()
            self._set_drag_active(True)
            return

        event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """Keep accepting a valid image while it moves over the widget."""
        if self.supported_file_from_mime_data(event.mimeData()) is not None:
            event.acceptProposedAction()
            return

        event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        """Restore the default appearance when a drag leaves the widget."""
        self._set_drag_active(False)
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        """Emit the selected file path after a successful drop."""
        self._set_drag_active(False)
        file_path = self.supported_file_from_mime_data(event.mimeData())

        if file_path is None:
            event.ignore()
            local_file = self.local_file_from_mime_data(event.mimeData())
            if local_file is None:
                message = "Перетащите локальный файл изображения"
            else:
                try:
                    validate_image_file(local_file, verify_content=False)
                except ImageValidationError as error:
                    message = str(error)
                else:
                    message = "Не удалось выбрать изображение"
            self.file_rejected.emit(message)
            return

        event.acceptProposedAction()
        self.file_selected.emit(str(file_path.resolve()))

    def _set_drag_active(self, is_active: bool) -> None:
        """Update text and the dynamic property used by the stylesheet."""
        if self.property("dragActive") == is_active:
            return

        self.setProperty("dragActive", is_active)
        self._title_label.setText(
            self.ACTIVE_TITLE if is_active else self.DEFAULT_TITLE
        )
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
