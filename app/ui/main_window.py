"""Main application window."""

import sqlite3
from pathlib import Path

from PySide6.QtCore import QThreadPool, Qt, Slot
from PySide6.QtGui import QResizeEvent
from PIL import Image
from PySide6.QtWidgets import (
    QFrame,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.models import ProcessingOptions, ProcessingResult
from app.services import HistoryService, ImageService
from app.ui.history_view import HistoryView
from app.ui.preview_widget import PreviewWidget
from app.ui.result_panel import ResultPanel
from app.ui.settings_panel import SettingsPanel
from app.ui.toast import ToastNotification
from app.workers import ImageWorker


class MainWindow(QMainWindow):
    """Top-level window of the Pixora application."""

    def __init__(
        self,
        image_service: ImageService,
        history_service: HistoryService,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Pixora")
        self.setMinimumSize(960, 640)
        self.resize(1180, 760)
        self.image_service = image_service
        self.history_service = history_service
        self.thread_pool = QThreadPool(self)
        self.processed_image: Image.Image | None = None
        self.processed_data: bytes | None = None
        self.processing_result: ProcessingResult | None = None
        self._active_worker: ImageWorker | None = None
        self._active_options: ProcessingOptions | None = None

        self._build_interface()
        self.result_panel = ResultPanel(self)
        self.result_panel.save_requested.connect(self._save_processed_image)
        self.history_view = HistoryView(self.history_service, self)
        self.toast = ToastNotification(self)

    def _build_interface(self) -> None:
        """Build the initial layout without image-processing behavior."""
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(32, 24, 32, 20)
        main_layout.setSpacing(24)
        main_layout.addWidget(self._create_header())
        main_layout.addLayout(self._create_intro())
        main_layout.addLayout(self._create_workspace(), stretch=1)

        self.setCentralWidget(central_widget)

        status_bar = QStatusBar(self)
        status_bar.setObjectName("statusBar")
        status_bar.showMessage("Готово к работе")
        self.setStatusBar(status_bar)

    def _create_header(self) -> QFrame:
        """Create the top navigation bar."""
        header = QFrame(self)
        header.setObjectName("header")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        brand_label = QLabel("PIXORA", header)
        brand_label.setObjectName("brandLabel")
        layout.addWidget(brand_label)
        layout.addStretch()

        self.history_button = QPushButton("История", header)
        self.history_button.setObjectName("historyButton")
        self.history_button.setFlat(True)
        self.history_button.clicked.connect(self._show_history)
        layout.addWidget(self.history_button)

        settings_button = QPushButton("Настройки", header)
        settings_button.setObjectName("settingsButton")
        settings_button.setFlat(True)
        settings_button.clicked.connect(self._focus_settings)
        layout.addWidget(settings_button)

        return header

    def _create_intro(self) -> QVBoxLayout:
        """Create the title and short application description."""
        layout = QVBoxLayout()
        layout.setSpacing(6)

        title_label = QLabel("Image Processing Toolbox", self)
        title_label.setObjectName("pageTitle")
        layout.addWidget(title_label)

        subtitle_label = QLabel("Быстрая обработка изображений на вашем компьютере", self)
        subtitle_label.setObjectName("pageSubtitle")
        layout.addWidget(subtitle_label)

        return layout

    def _create_workspace(self) -> QHBoxLayout:
        """Create preview and settings areas."""
        layout = QHBoxLayout()
        layout.setSpacing(24)
        layout.addWidget(self._create_preview_card(), stretch=2)
        layout.addWidget(self._create_settings_card(), stretch=1)
        return layout

    def _create_preview_card(self) -> QFrame:
        """Create the image drop and preview area."""
        preview_card = QFrame(self)
        preview_card.setObjectName("previewCard")
        preview_card.setFrameShape(QFrame.Shape.StyledPanel)
        preview_card.setMinimumHeight(420)
        preview_card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        layout = QVBoxLayout(preview_card)
        layout.setContentsMargins(20, 20, 20, 20)

        self.preview_widget = PreviewWidget(preview_card)
        self.preview_widget.file_selected.connect(self._handle_file_selected)
        self.preview_widget.file_rejected.connect(self._handle_file_rejected)
        layout.addWidget(self.preview_widget)
        return preview_card

    @Slot(str)
    def _handle_file_selected(self, file_path: str) -> None:
        """Acknowledge the path until preview loading is implemented."""
        self.statusBar().showMessage(
            f"Выбрано изображение: {Path(file_path).name}"
        )
        if self.preview_widget.image_info is not None:
            self.settings_panel.set_image_info(self.preview_widget.image_info)
        self.toast.show_message("Изображение загружено", "success", 2000)

    @Slot(str)
    def _handle_file_rejected(self, message: str) -> None:
        """Show a short validation message for an unsupported drop."""
        self.statusBar().showMessage(message, 5000)
        self.toast.show_message(message, "error")

    def _create_settings_card(self) -> QFrame:
        """Create the placeholder for processing settings."""
        settings_card = QFrame(self)
        settings_card.setObjectName("settingsCard")
        settings_card.setFrameShape(QFrame.Shape.StyledPanel)
        settings_card.setMinimumWidth(300)
        settings_card.setMaximumWidth(380)

        layout = QVBoxLayout(settings_card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title_label = QLabel("Настройки", settings_card)
        title_label.setObjectName("settingsTitle")
        layout.addWidget(title_label)

        self.settings_panel = SettingsPanel(settings_card)
        self.settings_panel.processing_requested.connect(self._process_image)
        layout.addWidget(self.settings_panel, stretch=1)
        return settings_card

    @Slot()
    def _process_image(self) -> None:
        """Collect UI settings and run the application service."""
        if self._active_worker is not None:
            return

        image_info = self.preview_widget.image_info
        if image_info is None:
            return

        options = self.settings_panel.processing_options()
        worker = ImageWorker(
            self.image_service,
            image_info.path,
            options,
        )
        worker.signals.finished.connect(self._handle_processing_finished)
        worker.signals.error.connect(self._handle_processing_error)
        self._active_worker = worker
        self._active_options = options
        self.settings_panel.set_processing(True)
        self.statusBar().showMessage("Обработка изображения...")
        self.thread_pool.start(worker)

    @Slot(object, bytes)
    def _handle_processing_finished(
        self,
        processed_image: Image.Image,
        encoded_data: bytes,
    ) -> None:
        """Store a completed image delivered from the worker thread."""
        if self.processed_image is not None:
            self.processed_image.close()
        self.processed_image = processed_image
        self.processed_data = encoded_data

        image_info = self.preview_widget.image_info
        options = self._active_options
        if image_info is not None and options is not None:
            output_format = options.output_format.strip().upper()
            if output_format == "JPG":
                output_format = "JPEG"
            self.processing_result = ProcessingResult(
                source=image_info,
                output_format=output_format,
                output_width=processed_image.width,
                output_height=processed_image.height,
                output_size=len(encoded_data),
                quality=options.quality,
            )
            self.result_panel.set_result(self.processing_result)
            self.result_panel.show()
            self.result_panel.raise_()

        self._active_worker = None
        self._active_options = None
        self.settings_panel.set_processing(False)
        self.statusBar().showMessage("Изображение успешно обработано")
        self.result_panel.toast.show_message(
            "Изображение успешно обработано",
            "success",
        )

    @Slot(str)
    def _handle_processing_error(self, message: str) -> None:
        """Show a worker failure without touching Pillow in the GUI layer."""
        self._active_worker = None
        self._active_options = None
        self.settings_panel.set_processing(False)
        self.statusBar().showMessage(message, 5000)
        self.toast.show_message(message, "error")

    @Slot()
    def _save_processed_image(self) -> None:
        """Ask for a destination and write the worker's encoded result bytes."""
        result = self.processing_result
        if result is None or self.processed_data is None:
            return

        extensions = {
            "JPEG": ((".jpg", ".jpeg"), ".jpg", "JPEG (*.jpg *.jpeg)"),
            "PNG": ((".png",), ".png", "PNG (*.png)"),
            "WEBP": ((".webp",), ".webp", "WEBP (*.webp)"),
        }
        valid_extensions, default_extension, file_filter = extensions[
            result.output_format
        ]
        suggested_name = f"{result.source.path.stem}_pixora{default_extension}"
        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить изображение",
            suggested_name,
            file_filter,
        )
        if not selected_path:
            return

        destination = Path(selected_path)
        if destination.suffix.lower() not in valid_extensions:
            destination = Path(f"{destination}{default_extension}")

        try:
            saved_path = self.image_service.save_encoded(
                self.processed_data,
                destination,
            )
        except OSError as error:
            self.statusBar().showMessage(str(error), 5000)
            self.result_panel.toast.show_message(str(error), "error")
            return

        try:
            self.history_service.record_processing(result, saved_path)
        except sqlite3.Error:
            self.result_panel.toast.show_message(
                "Файл сохранён, но историю обновить не удалось",
                "error",
            )
            return
        if self.history_view.isVisible():
            self.history_view.refresh()

        self.statusBar().showMessage(f"Изображение сохранено: {saved_path.name}")
        self.result_panel.toast.show_message(
            "Изображение успешно сохранено",
            "success",
        )

    @Slot()
    def _show_history(self) -> None:
        """Refresh and show the processing history dialog."""
        self.history_view.refresh()
        self.history_view.show()
        self.history_view.raise_()

    @Slot()
    def _focus_settings(self) -> None:
        """Move keyboard focus to the settings panel."""
        self.settings_panel.setFocus()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Keep overlay notifications anchored while the window resizes."""
        super().resizeEvent(event)
        toast = getattr(self, "toast", None)
        if toast is not None and toast.isVisible():
            toast.reposition()
