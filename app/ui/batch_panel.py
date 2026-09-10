"""Single-window interface for distributed batch processing."""

from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.models import ImageInfo
from app.ui.drop_zone import DropZoneWidget
from app.ui.settings_panel import SettingsPanel
from app.utils.validation import (
    DEFAULT_MAX_BATCH_FILES,
    ImageValidationError,
    validate_image_file,
)


class BatchPanel(QWidget):
    """Collect files and visualize execution across remote workers."""

    processing_requested = Signal(object, object)
    save_requested = Signal(object)
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("batchPanel")
        self._paths: list[Path] = []
        self._items_by_job_id: dict[str, QListWidgetItem] = {}
        self._last_status: dict[str, object] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(16)
        layout.addLayout(self._create_heading())

        content_layout = QHBoxLayout()
        content_layout.setSpacing(22)
        content_layout.addWidget(self._create_file_card(), stretch=2)
        content_layout.addWidget(self._create_settings_card(), stretch=1)
        layout.addLayout(content_layout, stretch=1)
        layout.addLayout(self._create_progress_row())

    def _create_heading(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(4)
        title = QLabel("Пакетная обработка", self)
        title.setObjectName("resultTitle")
        layout.addWidget(title)
        subtitle = QLabel(
            "Задания автоматически распределяются между Docker-workers",
            self,
        )
        subtitle.setObjectName("resultSubtitle")
        layout.addWidget(subtitle)
        return layout

    def _create_file_card(self) -> QFrame:
        card = QFrame(self)
        card.setObjectName("batchFileCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        self.file_count_label = QLabel("Изображения не выбраны", card)
        self.file_count_label.setObjectName("batchFileCount")
        header.addWidget(self.file_count_label, stretch=1)
        self.choose_files_button = QPushButton("Выбрать изображения", card)
        self.choose_files_button.setObjectName("chooseFileButton")
        self.choose_files_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.choose_files_button.clicked.connect(self.open_file_dialog)
        header.addWidget(self.choose_files_button)
        self.clear_files_button = QPushButton("Очистить", card)
        self.clear_files_button.setObjectName("secondaryButton")
        self.clear_files_button.setEnabled(False)
        self.clear_files_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_files_button.clicked.connect(self.clear_files)
        header.addWidget(self.clear_files_button)
        layout.addLayout(header)

        self.file_list = QListWidget(card)
        self.file_list.setObjectName("batchFileList")
        self.file_list.setAlternatingRowColors(True)
        layout.addWidget(self.file_list, stretch=1)

        hint = QLabel(
            f"До {DEFAULT_MAX_BATCH_FILES} файлов · каждый файл до 20 МБ · "
            "JPG, PNG или WEBP",
            card,
        )
        hint.setObjectName("dropHint")
        layout.addWidget(hint)
        return card

    def _create_settings_card(self) -> QFrame:
        card = QFrame(self)
        card.setObjectName("settingsCard")
        card.setMinimumWidth(310)
        card.setMaximumWidth(390)
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 12, 18)
        layout.setSpacing(12)
        title = QLabel("Настройки пакета", card)
        title.setObjectName("settingsTitle")
        layout.addWidget(title)

        scroll_area = QScrollArea(card)
        scroll_area.setObjectName("settingsScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.settings_panel = SettingsPanel(
            process_button_text="Запустить обработку"
        )
        self.settings_panel.processing_requested.connect(self._request_processing)
        scroll_area.setWidget(self.settings_panel)
        layout.addWidget(scroll_area, stretch=1)
        return card

    def _create_progress_row(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(12)
        self.status_label = QLabel("Выберите изображения для пакета", self)
        self.status_label.setObjectName("batchStatus")
        layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setObjectName("batchProgress")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar, stretch=1)
        self.save_button = QPushButton("Сохранить результаты", self)
        self.save_button.setObjectName("saveResultButton")
        self.save_button.setEnabled(False)
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.clicked.connect(self._request_save)
        layout.addWidget(self.save_button)
        self.cancel_button = QPushButton("Отменить", self)
        self.cancel_button.setObjectName("secondaryButton")
        self.cancel_button.setEnabled(False)
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.clicked.connect(self._request_cancel)
        layout.addWidget(self.cancel_button)
        return layout

    @Slot()
    def open_file_dialog(self) -> None:
        """Select and validate multiple independent input images."""
        selected_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите изображения",
            "",
            DropZoneWidget.IMAGE_FILTER,
        )
        if not selected_paths:
            return
        if len(selected_paths) > DEFAULT_MAX_BATCH_FILES:
            self.show_error(
                f"В одном пакете допускается не более "
                f"{DEFAULT_MAX_BATCH_FILES} файлов"
            )
            return
        paths: list[Path] = []
        try:
            for selected_path in selected_paths:
                paths.append(validate_image_file(selected_path).resolve())
        except ImageValidationError as error:
            self.show_error(str(error))
            return
        self.set_files(paths)

    def set_files(self, paths: list[Path]) -> None:
        """Populate the list and initialize settings from the first image."""
        if not paths:
            return
        if len(paths) > DEFAULT_MAX_BATCH_FILES:
            self.show_error(
                f"В одном пакете допускается не более "
                f"{DEFAULT_MAX_BATCH_FILES} файлов"
            )
            return
        self._paths = list(paths)
        self._items_by_job_id.clear()
        self._last_status = None
        self.file_list.clear()
        for path in paths:
            item = QListWidgetItem(f"○  {path.name} — ожидает запуска")
            item.setToolTip(str(path))
            self.file_list.addItem(item)

        first = paths[0]
        with Image.open(first) as image:
            width, height = image.size
            format_name = (image.format or first.suffix[1:]).upper()
        if format_name == "JPG":
            format_name = "JPEG"
        self.settings_panel.set_image_info(
            ImageInfo(
                path=first,
                filename=first.name,
                format=format_name,
                width=width,
                height=height,
                size=first.stat().st_size,
            )
        )
        self.file_count_label.setText(f"Выбрано изображений: {len(paths)}")
        self.clear_files_button.setEnabled(True)
        self._show_status("Пакет готов к отправке")
        self.progress_bar.setValue(0)
        self.save_button.setEnabled(False)

    def set_processing(self, is_processing: bool) -> None:
        """Lock file selection while a remote batch is active."""
        self.choose_files_button.setEnabled(not is_processing)
        self.clear_files_button.setEnabled(not is_processing and bool(self._paths))
        self.settings_panel.set_processing(is_processing)
        self.cancel_button.setEnabled(is_processing)
        if is_processing:
            self._show_status("Отправка пакета в очередь...")
            self.save_button.setEnabled(False)

    def set_batch_created(self, response: dict[str, object]) -> None:
        """Associate visible rows with server-generated task identifiers."""
        jobs = response.get("jobs", [])
        if not isinstance(jobs, list):
            return
        self._items_by_job_id.clear()
        for index, job in enumerate(jobs):
            if index >= self.file_list.count() or not isinstance(job, dict):
                continue
            job_id = str(job.get("job_id", ""))
            if job_id:
                self._items_by_job_id[job_id] = self.file_list.item(index)
            if job.get("queued") is False:
                filename = str(job.get("filename", "image"))
                self.file_list.item(index).setText(
                    f"✕  {filename} — не удалось поставить в очередь"
                )
        failed = int(response.get("failed_to_enqueue", 0))
        if failed:
            self._show_status(
                f"Пакет создан, не отправлено задач: {failed}",
                "error",
            )
        else:
            self._show_status("Задания поставлены в очередь")

    def update_batch_status(self, response: dict[str, object]) -> None:
        """Refresh aggregate progress and per-job worker attribution."""
        self._last_status = response
        progress = int(response.get("progress", 0))
        completed = int(response.get("completed", 0))
        failed = int(response.get("failed", 0))
        cancelled = int(response.get("cancelled", 0))
        total = int(response.get("total", len(self._paths)))
        self.progress_bar.setValue(progress)
        status_parts = [f"Готово: {completed} из {total}", f"ошибок: {failed}"]
        if cancelled:
            status_parts.append(f"отменено: {cancelled}")
        self._show_status(" · ".join(status_parts))

        jobs = response.get("jobs", [])
        if not isinstance(jobs, list):
            return
        for job in jobs:
            if not isinstance(job, dict):
                continue
            job_id = str(job.get("job_id", ""))
            item = self._items_by_job_id.get(job_id)
            if item is None:
                continue
            state = str(job.get("status", "PENDING"))
            filename = str(job.get("filename", "image"))
            worker = job.get("worker")
            if state == "SUCCESS":
                description = f"✓  {filename} — готово"
            elif state == "REVOKED":
                description = f"■  {filename} — отменено"
            elif state == "FAILURE":
                description = f"✕  {filename} — ошибка"
            elif state in {"RECEIVED", "STARTED", "PROCESSING", "RETRY"}:
                description = f"◉  {filename} — обрабатывается"
            else:
                description = f"○  {filename} — в очереди"
            if worker:
                description = f"{description} · {worker}"
            item.setText(description)

    def finish_batch(self, response: dict[str, object]) -> None:
        """Unlock controls and expose download when results are available."""
        self.update_batch_status(response)
        self.set_processing(False)
        completed = int(response.get("completed", 0))
        self.save_button.setEnabled(completed > 0)
        self.cancel_button.setEnabled(False)

    def show_error(self, message: str) -> None:
        """Show a non-modal error without leaving the batch page."""
        self.set_processing(False)
        self._show_status(message, "error")

    @Slot()
    def clear_files(self) -> None:
        """Reset the pending batch without recreating the page."""
        self._paths.clear()
        self._items_by_job_id.clear()
        self._last_status = None
        self.file_list.clear()
        self.file_count_label.setText("Изображения не выбраны")
        self.settings_panel.clear_image_info()
        self.clear_files_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self._show_status("Выберите изображения для пакета")

    def show_saved(self, count: int, directory: Path) -> None:
        """Acknowledge a completed multi-file download."""
        self._show_status(f"Сохранено файлов: {count} · {directory}", "success")
        self.save_button.setEnabled(True)

    def _show_status(self, message: str, kind: str = "normal") -> None:
        """Set status text and refresh its dynamic color property."""
        self.status_label.setProperty("kind", kind)
        self.status_label.setText(message)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    @Slot()
    def _request_processing(self) -> None:
        if self._paths:
            self.processing_requested.emit(
                list(self._paths),
                self.settings_panel.processing_options(),
            )

    @Slot()
    def _request_save(self) -> None:
        if self._last_status is None:
            return
        jobs = self._last_status.get("jobs", [])
        if isinstance(jobs, list):
            self.save_requested.emit(jobs)

    @Slot()
    def _request_cancel(self) -> None:
        self.cancel_button.setEnabled(False)
        self._show_status("Отмена незавершённых задач...")
        self.cancel_requested.emit()
