"""Dialog for browsing image processing history."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QLabel,
    QPushButton,
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

        close_button = QPushButton("Закрыть", self)
        close_button.setObjectName("secondaryButton")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)

    def refresh(self) -> None:
        """Reload history records from the service."""
        records = self.history_service.get_history()
        self.table.setRowCount(len(records))
        for row_index, record in enumerate(records):
            self._fill_row(row_index, record)

        self._stack.setCurrentWidget(self.table if records else self._empty_label)

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
