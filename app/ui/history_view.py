"""Dialog for browsing image processing history."""

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models import HistoryRecord
from app.services import HistoryService
from app.utils.file_utils import format_file_size


class HistoryView(QDialog):
    """Display persisted processing operations in a read-only table."""

    HEADERS = ("Дата", "Файл", "Форматы", "Разрешение", "Размер", "Экономия")
    open_requested = Signal(str)

    def __init__(
        self,
        history_service: HistoryService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.history_service = history_service
        self.setObjectName("historyView")
        self.setWindowTitle("История обработки")
        self.setMinimumSize(900, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title_label = QLabel("История обработки", self)
        title_label.setObjectName("historyTitle")
        layout.addWidget(title_label)

        content = QWidget(self)
        self._stack = QStackedLayout(content)
        self._stack.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(content)
        self.table.setObjectName("historyTable")
        self.table.setColumnCount(len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setToolTip(
            "Дважды щёлкните строку, чтобы открыть сохранённое изображение"
        )
        self.table.cellDoubleClicked.connect(self._request_open)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )
        self._stack.addWidget(self.table)

        empty_label = QLabel("История пока пуста", content)
        empty_label.setObjectName("historyEmptyLabel")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stack.addWidget(empty_label)
        self._empty_label = empty_label

        layout.addWidget(content, stretch=1)

        actions_layout = QHBoxLayout()

        self.clear_button = QPushButton("Очистить историю", self)
        self.clear_button.setObjectName("dangerButton")
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.clicked.connect(self._confirm_clear)
        actions_layout.addWidget(self.clear_button)
        actions_layout.addStretch()

        close_button = QPushButton("Закрыть", self)
        close_button.setObjectName("secondaryButton")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(self.close)
        actions_layout.addWidget(close_button)
        layout.addLayout(actions_layout)

    def refresh(self) -> None:
        """Reload history records from the service."""
        records = self.history_service.get_history()
        self.table.setRowCount(len(records))
        for row_index, record in enumerate(records):
            self._fill_row(row_index, record)

        self.clear_button.setEnabled(bool(records))
        self._stack.setCurrentWidget(self.table if records else self._empty_label)

    def _confirm_clear(self) -> None:
        """Ask for confirmation and clear all history records."""
        answer = QMessageBox.question(
            self,
            "Очистить историю?",
            "Все записи истории будут удалены. Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.history_service.clear_history()
        self.refresh()

    @Slot(int, int)
    def _request_open(self, row_index: int, _column_index: int) -> None:
        """Ask the main window to open the result associated with a row."""
        item = self.table.item(row_index, 0)
        if item is None:
            return
        output_path = item.data(Qt.ItemDataRole.UserRole)
        if output_path:
            self.open_requested.emit(str(output_path))

    def _fill_row(self, row_index: int, record: HistoryRecord) -> None:
        """Render one history record into a table row."""
        created_at = (
            record.created_at.strftime("%d.%m.%Y %H:%M")
            if record.created_at is not None
            else "—"
        )
        savings = record.saved_percentage
        savings_text = f"{savings:.1f}%"
        values = (
            created_at,
            record.original_filename,
            f"{record.original_format} → {record.output_format}",
            (
                f"{record.original_width}×{record.original_height} → "
                f"{record.output_width}×{record.output_height}"
            ),
            (
                f"{format_file_size(record.original_size)} → "
                f"{format_file_size(record.output_size)}"
            ),
            savings_text,
        )

        for column_index, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setData(Qt.ItemDataRole.UserRole, str(record.output_path))
            if column_index in {0, 2, 3, 4, 5}:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_index, column_index, item)
