"""Single-window interface for distributed batch processing."""

from pathlib import Path
from time import monotonic

from PIL import Image
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor
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


class ClusterNodeWidget(QFrame):
    """Compact service or worker card used in the live cluster diagram."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("clusterNode")
        self.setProperty("state", "unknown")
        self.setMinimumWidth(112)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)
        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("clusterNodeTitle")
        self.detail_label = QLabel("Проверка...", self)
        self.detail_label.setObjectName("clusterNodeDetail")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.detail_label)

    def set_state(self, detail: str, state: str) -> None:
        """Update text and repolish the card after a dynamic state change."""
        self.setProperty("state", state)
        self.detail_label.setText(detail)
        self.style().unpolish(self)
        self.style().polish(self)


class BatchPanel(QWidget):
    """Collect files and visualize execution across remote workers."""

    processing_requested = Signal(object, object)
    save_requested = Signal(object)
    cancel_requested = Signal()
    cluster_refresh_requested = Signal()

    WORKER_COLORS = ("#a78bfa", "#22d3ee", "#f5b85c", "#55d6a6")
    ACTIVE_STATES = frozenset({"RECEIVED", "STARTED", "PROCESSING", "RETRY"})

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("batchPanel")
        self._paths: list[Path] = []
        self._items_by_job_id: dict[str, QListWidgetItem] = {}
        self._last_status: dict[str, object] | None = None
        self._cluster_status: dict[str, object] | None = None
        self._worker_nodes: dict[str, ClusterNodeWidget] = {}
        self._worker_display_names: dict[str, str] = {}
        self._processing = False
        self._started_at: float | None = None
        self._elapsed_seconds: float | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(12)
        layout.addLayout(self._create_heading())
        layout.addWidget(self._create_cluster_card())

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

    def _create_cluster_card(self) -> QFrame:
        card = QFrame(self)
        card.setObjectName("clusterCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Живой кластер", card)
        title.setObjectName("clusterTitle")
        header.addWidget(title)
        self.cluster_state_label = QLabel("Получаем состояние сервисов", card)
        self.cluster_state_label.setObjectName("clusterSummary")
        header.addWidget(self.cluster_state_label, stretch=1)
        self.refresh_cluster_button = QPushButton("Обновить", card)
        self.refresh_cluster_button.setObjectName("compactButton")
        self.refresh_cluster_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_cluster_button.clicked.connect(
            self.cluster_refresh_requested.emit
        )
        header.addWidget(self.refresh_cluster_button)
        layout.addLayout(header)

        flow = QHBoxLayout()
        flow.setSpacing(8)
        self.api_node = ClusterNodeWidget("FastAPI", card)
        flow.addWidget(self.api_node)
        flow.addWidget(self._cluster_arrow(card))
        self.redis_node = ClusterNodeWidget("Redis", card)
        flow.addWidget(self.redis_node)
        flow.addWidget(self._cluster_arrow(card))

        self.worker_lane = QFrame(card)
        self.worker_lane.setObjectName("workerLane")
        self.worker_layout = QHBoxLayout(self.worker_lane)
        self.worker_layout.setContentsMargins(0, 0, 0, 0)
        self.worker_layout.setSpacing(8)
        self.worker_placeholder = ClusterNodeWidget("Workers", self.worker_lane)
        self.worker_placeholder.set_state("Проверка узлов...", "unknown")
        self.worker_layout.addWidget(self.worker_placeholder)
        flow.addWidget(self.worker_lane, stretch=1)

        flow.addWidget(self._cluster_arrow(card))
        self.minio_node = ClusterNodeWidget("MinIO", card)
        flow.addWidget(self.minio_node)
        layout.addLayout(flow)

        self.distribution_label = QLabel(
            "Здесь будет видно, какой worker получил каждое изображение",
            card,
        )
        self.distribution_label.setObjectName("distributionSummary")
        layout.addWidget(self.distribution_label)
        return card

    @staticmethod
    def _cluster_arrow(parent: QWidget) -> QLabel:
        arrow = QLabel("→", parent)
        arrow.setObjectName("clusterArrow")
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return arrow

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
            process_button_text="Запустить обработку",
            format_selection_enabled=False,
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

    def set_cluster_loading(self, loading: bool) -> None:
        """Reflect a one-shot background cluster refresh."""
        self.refresh_cluster_button.setEnabled(not loading)
        if loading and self._cluster_status is None:
            self.cluster_state_label.setText("Проверяем подключение...")

    def update_cluster_status(self, response: dict[str, object]) -> None:
        """Render a real snapshot returned by the distributed API."""
        self._cluster_status = response
        self.refresh_cluster_button.setEnabled(True)
        api_online = response.get("api") == "online"
        redis_online = response.get("redis") == "online"
        minio_online = response.get("minio") == "online"
        queue_depth = response.get("queue_depth")

        self.api_node.set_state(
            "Координатор доступен" if api_online else "Нет связи",
            "online" if api_online else "offline",
        )
        queue_text = "Очередь недоступна"
        if redis_online:
            queue_text = f"В очереди: {queue_depth if queue_depth is not None else 0}"
        self.redis_node.set_state(
            queue_text,
            "online" if redis_online else "offline",
        )
        self.minio_node.set_state(
            "Хранилище доступно" if minio_online else "Нет связи",
            "online" if minio_online else "offline",
        )

        workers = response.get("workers", [])
        if not isinstance(workers, list):
            workers = []
        for worker in workers:
            if isinstance(worker, dict) and worker.get("worker_id"):
                self._ensure_worker_node(str(worker["worker_id"]))

        if not self._worker_nodes:
            self.worker_placeholder.show()
            self.worker_placeholder.set_state("Нет доступных узлов", "offline")
        else:
            self.worker_placeholder.hide()
        self._refresh_worker_nodes()

        online_services = sum((api_online, redis_online, minio_online))
        self.cluster_state_label.setText(
            f"Сервисы: {online_services}/3 · workers онлайн: {len(workers)}"
        )
        self.cluster_state_label.setProperty(
            "state", "online" if online_services == 3 and workers else "warning"
        )
        self.cluster_state_label.style().unpolish(self.cluster_state_label)
        self.cluster_state_label.style().polish(self.cluster_state_label)
        self._update_distribution_summary()

    def show_cluster_error(self, message: str) -> None:
        """Keep the processing page usable when monitoring is unavailable."""
        self.refresh_cluster_button.setEnabled(True)
        self.cluster_state_label.setText("Не удалось получить состояние кластера")
        self.cluster_state_label.setToolTip(message)
        for node in (self.api_node, self.redis_node, self.minio_node):
            node.set_state("Нет связи", "offline")
        for node in self._worker_nodes.values():
            node.set_state("Нет связи", "offline")

    def _ensure_worker_node(self, worker_id: str) -> ClusterNodeWidget:
        existing = self._worker_nodes.get(worker_id)
        if existing is not None:
            return existing
        number = len(self._worker_nodes) + 1
        display_name = f"Worker {number}"
        node = ClusterNodeWidget(display_name, self.worker_lane)
        node.title_label.setStyleSheet(
            f"color: {self.WORKER_COLORS[(number - 1) % len(self.WORKER_COLORS)]};"
        )
        node.setToolTip(worker_id)
        self._worker_nodes[worker_id] = node
        self._worker_display_names[worker_id] = display_name
        self.worker_layout.addWidget(node)
        self.worker_placeholder.hide()
        return node

    def _refresh_worker_nodes(self) -> None:
        workers = []
        if self._cluster_status is not None:
            value = self._cluster_status.get("workers", [])
            if isinstance(value, list):
                workers = [item for item in value if isinstance(item, dict)]
        live_workers = {
            str(worker.get("worker_id")): worker
            for worker in workers
            if worker.get("worker_id")
        }
        jobs = self._current_jobs()
        for job in jobs:
            worker_id = job.get("worker")
            if worker_id:
                self._ensure_worker_node(str(worker_id))

        for worker_id, node in self._worker_nodes.items():
            assigned = [job for job in jobs if str(job.get("worker", "")) == worker_id]
            active = [
                job for job in assigned if str(job.get("status")) in self.ACTIVE_STATES
            ]
            completed = sum(job.get("status") == "SUCCESS" for job in assigned)
            live = live_workers.get(worker_id)
            if active:
                filename = str(active[0].get("filename", "изображение"))
                node.set_state(f"Сейчас: {filename}", "busy")
            elif live is not None and live.get("status") == "busy":
                active_tasks = int(live.get("active_tasks", 0))
                node.set_state(f"Активных задач: {active_tasks}", "busy")
            elif live is not None:
                node.set_state(f"Свободен · готово: {completed}", "online")
            elif self._cluster_status is not None:
                node.set_state("Нет связи", "offline")
            else:
                node.set_state(f"Готово: {completed}", "unknown")

    def _current_jobs(self) -> list[dict[str, object]]:
        if self._last_status is None:
            return []
        jobs = self._last_status.get("jobs", [])
        if not isinstance(jobs, list):
            return []
        return [job for job in jobs if isinstance(job, dict)]

    def _worker_name(self, worker_id: str) -> str:
        self._ensure_worker_node(worker_id)
        return self._worker_display_names[worker_id]

    def _worker_color(self, worker_id: str) -> str:
        self._ensure_worker_node(worker_id)
        number = list(self._worker_nodes).index(worker_id)
        return self.WORKER_COLORS[number % len(self.WORKER_COLORS)]

    def _update_distribution_summary(self) -> None:
        jobs = self._current_jobs()
        counts: dict[str, int] = {}
        for job in jobs:
            worker = job.get("worker")
            if worker:
                worker_id = str(worker)
                counts[worker_id] = counts.get(worker_id, 0) + 1

        if counts:
            parts = [
                f"{self._worker_name(worker_id)} — {count}"
                for worker_id, count in counts.items()
            ]
            elapsed = self._elapsed_seconds
            if self._processing and self._started_at is not None:
                elapsed = monotonic() - self._started_at
            if elapsed is not None:
                parts.append(f"время: {elapsed:.1f} с")
            self.distribution_label.setText("Распределено: " + " · ".join(parts))
            return

        if self._cluster_status is not None:
            queue_depth = self._cluster_status.get("queue_depth")
            queue_text = queue_depth if queue_depth is not None else "—"
            workers = self._cluster_status.get("workers", [])
            worker_count = len(workers) if isinstance(workers, list) else 0
            self.distribution_label.setText(
                f"Готово к работе: workers {worker_count} · в очереди {queue_text}"
            )

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
            item.setData(Qt.ItemDataRole.UserRole, str(path))
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
        self._started_at = None
        self._elapsed_seconds = None
        self._update_distribution_summary()

    def set_processing(self, is_processing: bool) -> None:
        """Lock file selection while a remote batch is active."""
        was_processing = self._processing
        self._processing = is_processing
        if is_processing and not was_processing:
            self._started_at = monotonic()
            self._elapsed_seconds = None
        elif not is_processing and was_processing and self._started_at is not None:
            self._elapsed_seconds = monotonic() - self._started_at
        self.choose_files_button.setEnabled(not is_processing)
        self.clear_files_button.setEnabled(not is_processing and bool(self._paths))
        self.settings_panel.set_processing(is_processing)
        self.cancel_button.setEnabled(is_processing)
        if is_processing:
            self._show_status("Отправка пакета в очередь...")
            self.save_button.setEnabled(False)
        self._update_distribution_summary()

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
            elif state in self.ACTIVE_STATES:
                description = f"◉  {filename} — обрабатывается"
            else:
                description = f"○  {filename} — в очереди"
            if worker:
                worker_id = str(worker)
                description = f"{description} · {self._worker_name(worker_id)}"
                item.setForeground(QColor(self._worker_color(worker_id)))
                source_path = item.data(Qt.ItemDataRole.UserRole) or filename
                item.setToolTip(f"{source_path}\n{worker_id}")
            else:
                item.setForeground(QColor("#c8d0dc"))
            item.setText(description)
        self._refresh_worker_nodes()
        self._update_distribution_summary()

    def finish_batch(self, response: dict[str, object]) -> None:
        """Unlock controls and expose download when results are available."""
        self.update_batch_status(response)
        self.set_processing(False)
        completed = int(response.get("completed", 0))
        self.save_button.setEnabled(completed > 0)
        self.cancel_button.setEnabled(False)
        self._refresh_worker_nodes()
        self._update_distribution_summary()

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
        self._processing = False
        self._started_at = None
        self._elapsed_seconds = None
        self._show_status("Выберите изображения для пакета")
        self._refresh_worker_nodes()
        self._update_distribution_summary()

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
