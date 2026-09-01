"""Drag-and-drop area for selecting an image."""

from pathlib import Path

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import (
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
)
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class DropZoneWidget(QWidget):
    """Accept supported local image files dropped by the user."""

    SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})
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

        hint_label = QLabel("JPG · PNG · WEBP", self)
        hint_label.setObjectName("dropHint")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint_label)

    @classmethod
    def supported_file_from_mime_data(cls, mime_data: QMimeData) -> Path | None:
        """Return the first supported local image from MIME data."""
        if not mime_data.hasUrls():
            return None

        for url in mime_data.urls():
            if not url.isLocalFile():
                continue

            file_path = Path(url.toLocalFile())
            if (
                file_path.suffix.lower() in cls.SUPPORTED_EXTENSIONS
                and file_path.is_file()
            ):
                return file_path

        return None

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
            self.file_rejected.emit("Поддерживаются только JPG, PNG и WEBP")
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
