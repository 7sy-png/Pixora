"""Main application window."""

from os import getenv
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QThreadPool, Qt, Slot
from PySide6.QtGui import QCloseEvent, QIcon, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.models import ProcessingOptions, ProcessingResult
from app.services import DistributedClient, ImageService
from app.ui.batch_panel import BatchPanel
from app.ui.preview_widget import PreviewWidget
from app.ui.result_panel import ResultPanel
from app.ui.settings_panel import SettingsPanel
from app.ui.theme import APP_ICON_PATH, LOGO_PATH
from app.workers import (
    DistributedBatchWorker,
    DistributedClusterWorker,
    DistributedDownloadWorker,
    ImageWorker,
)


class MainWindow(QMainWindow):
    """Top-level window of the Pixora application."""

    def __init__(
        self,
        image_service: ImageService,
        distributed_client: DistributedClient | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Pixora")
        self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.setMinimumSize(960, 640)
        self.resize(1180, 760)
        self.image_service = image_service
        self.distributed_client = distributed_client or DistributedClient(
            getenv("PIXORA_API_URL", "http://127.0.0.1:8000")
        )
        self.thread_pool = QThreadPool(self)
        self.processed_image: Image.Image | None = None
        self.processed_data: bytes | None = None
        self.processing_result: ProcessingResult | None = None
        self._active_worker: ImageWorker | None = None
        self._active_options: ProcessingOptions | None = None
        self._active_batch_worker: DistributedBatchWorker | None = None
        self._active_cluster_worker: DistributedClusterWorker | None = None
        self._active_download_worker: DistributedDownloadWorker | None = None

        self._build_interface()

    def _build_interface(self) -> None:
        """Build the branded header and single-window content stack."""
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(32, 20, 32, 16)
        main_layout.setSpacing(18)
        main_layout.addWidget(self._create_header())

        self.content_stack = QStackedWidget(central_widget)
        self.content_stack.setObjectName("contentStack")
        self.workspace_page = self._create_workspace()
        self.result_panel = ResultPanel(self.content_stack)
        self.result_panel.save_requested.connect(self._save_processed_image)
        self.result_panel.back_requested.connect(self._show_workspace)
        self.content_stack.addWidget(self.workspace_page)
        self.content_stack.addWidget(self.result_panel)
        self.batch_panel = BatchPanel(self.content_stack)
        self.batch_panel.processing_requested.connect(self._process_batch)
        self.batch_panel.save_requested.connect(self._save_batch_results)
        self.batch_panel.cancel_requested.connect(self._cancel_batch)
        self.batch_panel.cluster_refresh_requested.connect(
            self._refresh_cluster_status
        )
        self.content_stack.addWidget(self.batch_panel)
        main_layout.addWidget(self.content_stack, stretch=1)

        self.setCentralWidget(central_widget)

        status_bar = QStatusBar(self)
        status_bar.setObjectName("statusBar")
        status_bar.showMessage("Готово к работе")
        self.setStatusBar(status_bar)

    def _create_header(self) -> QFrame:
        """Create the compact Pixora brand header."""
        header = QFrame(self)
        header.setObjectName("header")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        logo_label = QLabel(header)
        logo_label.setObjectName("brandIcon")
        logo_label.setFixedSize(38, 38)
        logo_label.setPixmap(
            QPixmap(str(LOGO_PATH)).scaled(
                38,
                38,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        layout.addWidget(logo_label)

        brand_label = QLabel("PIXORA", header)
        brand_label.setObjectName("brandLabel")
        layout.addWidget(brand_label)
        layout.addStretch()

        self.batch_mode_button = QPushButton("Пакетная обработка", header)
        self.batch_mode_button.setObjectName("secondaryButton")
        self.batch_mode_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.batch_mode_button.clicked.connect(self._toggle_processing_mode)
        layout.addWidget(self.batch_mode_button)
        return header

    def _create_workspace(self) -> QWidget:
        """Create the preview and processing settings page."""
        page = QWidget(self)
        page.setObjectName("workspacePage")
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(22)
        layout.addWidget(self._create_preview_card(page), stretch=2)
        layout.addWidget(self._create_settings_card(page), stretch=1)
        return page

    def _create_preview_card(self, parent: QWidget) -> QFrame:
        """Create the image drop and preview area."""
        preview_card = QFrame(parent)
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

    def _create_settings_card(self, parent: QWidget) -> QFrame:
        """Create the scrollable processing settings card."""
        settings_card = QFrame(parent)
        settings_card.setObjectName("settingsCard")
        settings_card.setFrameShape(QFrame.Shape.StyledPanel)
        settings_card.setMinimumWidth(310)
        settings_card.setMaximumWidth(390)

        layout = QVBoxLayout(settings_card)
        layout.setContentsMargins(22, 20, 12, 18)
        layout.setSpacing(12)

        title_label = QLabel("Настройки", settings_card)
        title_label.setObjectName("settingsTitle")
        layout.addWidget(title_label)

        self.settings_scroll_area = QScrollArea(settings_card)
        self.settings_scroll_area.setObjectName("settingsScrollArea")
        self.settings_scroll_area.setWidgetResizable(True)
        self.settings_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.settings_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.settings_scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.settings_panel = SettingsPanel()
        self.settings_panel.processing_requested.connect(self._process_image)
        self.settings_panel.preview_transform_changed.connect(
            self.preview_widget.set_transform
        )
        self.settings_panel.preview_dimensions_changed.connect(
            self.preview_widget.set_output_size
        )
        self.settings_scroll_area.setWidget(self.settings_panel)
        layout.addWidget(self.settings_scroll_area, stretch=1)
        return settings_card

    @Slot(str)
    def _handle_file_selected(self, file_path: str) -> None:
        """Populate settings and acknowledge the selected image."""
        self.statusBar().showMessage(f"Выбрано изображение: {Path(file_path).name}")
        if self.preview_widget.image_info is not None:
            self.settings_panel.set_image_info(self.preview_widget.image_info)

    @Slot(str)
    def _handle_file_rejected(self, message: str) -> None:
        """Show validation feedback in the permanent status bar."""
        self.statusBar().showMessage(message, 5000)

    @Slot()
    def _process_image(self) -> None:
        """Collect UI settings and run the application service."""
        if self._active_worker is not None or self._active_batch_worker is not None:
            return

        image_info = self.preview_widget.image_info
        if image_info is None:
            return

        options = self.settings_panel.processing_options()
        worker = ImageWorker(self.image_service, image_info.path, options)
        worker.signals.finished.connect(self._handle_processing_finished)
        worker.signals.error.connect(self._handle_processing_error)
        self._active_worker = worker
        self._active_options = options
        self.settings_panel.set_processing(True)
        self.batch_mode_button.setEnabled(False)
        self.statusBar().showMessage("Обработка изображения...")
        self.thread_pool.start(worker)

    @Slot(object, bytes)
    def _handle_processing_finished(
        self,
        processed_image: Image.Image,
        encoded_data: bytes,
    ) -> None:
        """Display a completed result on the main window's result page."""
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
            self.result_panel.set_result(self.processing_result, encoded_data)
            self.content_stack.setCurrentWidget(self.result_panel)

        self._active_worker = None
        self._active_options = None
        self.settings_panel.set_processing(False)
        self.batch_mode_button.setEnabled(True)
        self.statusBar().showMessage("Изображение успешно обработано")

    @Slot(str)
    def _handle_processing_error(self, message: str) -> None:
        """Restore controls and show a worker failure in the status bar."""
        self._active_worker = None
        self._active_options = None
        self.settings_panel.set_processing(False)
        self.batch_mode_button.setEnabled(True)
        self.statusBar().showMessage(message, 5000)

    @Slot()
    def _save_processed_image(self) -> None:
        """Ask for a destination and write the encoded result bytes."""
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
            message = str(error)
            self.statusBar().showMessage(message, 5000)
            self.result_panel.show_status(message, "error")
            return

        message = f"Сохранено: {saved_path.name}"
        self.statusBar().showMessage(f"Изображение сохранено: {saved_path.name}")
        self.result_panel.show_status(message)

    @Slot()
    def _show_workspace(self) -> None:
        """Return from the inline result page to the existing settings."""
        self.result_panel.clear_status()
        self.content_stack.setCurrentWidget(self.workspace_page)
        self.batch_mode_button.setText("Пакетная обработка")
        self.statusBar().showMessage("Можно изменить настройки и обработать снова")

    @Slot()
    def _toggle_processing_mode(self) -> None:
        """Switch between individual and distributed processing pages."""
        if self.content_stack.currentWidget() is self.batch_panel:
            self._show_workspace()
            return
        self.content_stack.setCurrentWidget(self.batch_panel)
        self.batch_mode_button.setText("Обычный режим")
        self.statusBar().showMessage("Распределённая пакетная обработка")
        self._refresh_cluster_status()

    @Slot()
    def _refresh_cluster_status(self) -> None:
        """Load service and worker state without blocking the GUI thread."""
        if self._active_cluster_worker is not None:
            return
        worker = DistributedClusterWorker(self.distributed_client)
        worker.signals.finished.connect(self._handle_cluster_status)
        worker.signals.error.connect(self._handle_cluster_status_error)
        self._active_cluster_worker = worker
        self.batch_panel.set_cluster_loading(True)
        self.thread_pool.start(worker)

    @Slot(object)
    def _handle_cluster_status(self, response: dict[str, object]) -> None:
        self._active_cluster_worker = None
        self.batch_panel.update_cluster_status(response)

    @Slot(str)
    def _handle_cluster_status_error(self, message: str) -> None:
        self._active_cluster_worker = None
        self.batch_panel.show_cluster_error(message)

    @Slot(object, object)
    def _process_batch(
        self,
        image_paths: list[Path],
        options: ProcessingOptions,
    ) -> None:
        """Submit multiple files to the API from a background Qt worker."""
        if self._active_batch_worker is not None or self._active_worker is not None:
            return
        worker = DistributedBatchWorker(
            self.distributed_client,
            image_paths,
            options,
        )
        worker.signals.submitted.connect(self.batch_panel.set_batch_created)
        worker.signals.progress.connect(self.batch_panel.update_batch_status)
        worker.signals.cluster.connect(self.batch_panel.update_cluster_status)
        worker.signals.finished.connect(self._handle_batch_finished)
        worker.signals.error.connect(self._handle_batch_error)
        worker.signals.cancelled.connect(self._handle_batch_cancelled)
        self._active_batch_worker = worker
        self.batch_panel.set_processing(True)
        self.batch_mode_button.setEnabled(False)
        self.statusBar().showMessage("Пакет отправляется в распределённую очередь...")
        self.thread_pool.start(worker)

    @Slot(object)
    def _handle_batch_finished(self, response: dict[str, object]) -> None:
        """Show final batch totals without opening another window."""
        self._active_batch_worker = None
        self.batch_panel.finish_batch(response)
        self.batch_mode_button.setEnabled(True)
        completed = int(response.get("completed", 0))
        failed = int(response.get("failed", 0))
        cancelled = int(response.get("cancelled", 0))
        self.statusBar().showMessage(
            f"Пакет завершён: готово {completed}, ошибок {failed}, "
            f"отменено {cancelled}"
        )

    @Slot(str)
    def _handle_batch_error(self, message: str) -> None:
        """Restore the batch controls after an API or worker failure."""
        self._active_batch_worker = None
        self.batch_panel.show_error(message)
        self.batch_mode_button.setEnabled(True)
        self.statusBar().showMessage(message, 5000)

    @Slot()
    def _handle_batch_cancelled(self) -> None:
        """Restore controls after polling is stopped during application exit."""
        self._active_batch_worker = None
        self.batch_panel.set_processing(False)
        self.batch_mode_button.setEnabled(True)
        self.statusBar().showMessage("Пакетная обработка отменена")

    @Slot()
    def _cancel_batch(self) -> None:
        """Cancel remote pending jobs without blocking the GUI thread."""
        if self._active_batch_worker is not None:
            self._active_batch_worker.cancel(remote=True)

    @Slot(object)
    def _save_batch_results(self, jobs: list[dict[str, object]]) -> None:
        """Select a directory and download all successful task outputs."""
        if self._active_download_worker is not None:
            return
        selected_directory = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для результатов",
        )
        if not selected_directory:
            return

        worker = DistributedDownloadWorker(
            self.distributed_client,
            jobs,
            Path(selected_directory),
        )
        worker.signals.finished.connect(self._handle_batch_saved)
        worker.signals.error.connect(self._handle_batch_save_error)
        self._active_download_worker = worker
        self.batch_panel.save_button.setEnabled(False)
        self.statusBar().showMessage("Скачивание результатов...")
        self.thread_pool.start(worker)

    @Slot(object)
    def _handle_batch_saved(self, saved_paths: list[Path]) -> None:
        """Confirm that every available result was downloaded."""
        self._active_download_worker = None
        if not saved_paths:
            self.batch_panel.show_error("Нет готовых результатов для сохранения")
            return
        self.batch_panel.show_saved(len(saved_paths), saved_paths[0].parent)
        self.statusBar().showMessage(f"Сохранено файлов: {len(saved_paths)}")

    @Slot(str)
    def _handle_batch_save_error(self, message: str) -> None:
        """Expose download errors inline and allow a retry."""
        self._active_download_worker = None
        self.batch_panel.show_error(message)
        self.batch_panel.save_button.setEnabled(True)
        self.statusBar().showMessage(message, 5000)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Release the retained Pillow image before closing the application."""
        if self._active_batch_worker is not None:
            self._active_batch_worker.cancel(remote=False)
        if self.processed_image is not None:
            self.processed_image.close()
            self.processed_image = None
        super().closeEvent(event)
