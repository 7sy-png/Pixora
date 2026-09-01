"""Dialog that presents image processing results."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models import ProcessingResult
from app.utils.file_utils import format_file_size


class ResultPanel(QDialog):
    """Compare source and output metadata after successful processing."""

    save_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("resultPanel")
        self.setWindowTitle("Результат обработки")
        self.setMinimumSize(560, 380)
        self.setModal(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(20)

        title_label = QLabel("Изображение обработано", self)
        title_label.setObjectName("resultTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        comparison_layout = QHBoxLayout()
        comparison_layout.setSpacing(16)
        source_card, self._source_labels = self._create_summary_card("Исходник")
        output_card, self._output_labels = self._create_summary_card("Результат")
        comparison_layout.addWidget(source_card)
        comparison_layout.addWidget(output_card)
        layout.addLayout(comparison_layout)

        self._savings_label = QLabel(self)
        self._savings_label.setObjectName("savingsLabel")
        self._savings_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._savings_label)
        layout.addStretch()

        actions_layout = QHBoxLayout()
        actions_layout.addStretch()

        self.save_button = QPushButton("Сохранить изображение", self)
        self.save_button.setObjectName("saveResultButton")
        self.save_button.clicked.connect(self.save_requested)
        actions_layout.addWidget(self.save_button)

        close_button = QPushButton("Закрыть", self)
        close_button.setObjectName("secondaryButton")
        close_button.clicked.connect(self.close)
        actions_layout.addWidget(close_button)
        layout.addLayout(actions_layout)

    def set_result(self, result: ProcessingResult) -> None:
        """Populate the comparison cards and signed savings message."""
        self._source_labels["format"].setText(result.source.format)
        self._source_labels["resolution"].setText(
            f"{result.source.width} × {result.source.height}"
        )
        self._source_labels["size"].setText(format_file_size(result.source.size))

        self._output_labels["format"].setText(result.output_format)
        self._output_labels["resolution"].setText(
            f"{result.output_width} × {result.output_height}"
        )
        self._output_labels["size"].setText(format_file_size(result.output_size))

        savings = result.saved_percentage
        self._savings_label.setProperty("increased", savings < 0)
        if savings >= 0:
            message = f"Размер уменьшен на {savings:.1f}%"
        else:
            message = f"Размер увеличен на {abs(savings):.1f}%"
        self._savings_label.setText(message)
        self._savings_label.style().unpolish(self._savings_label)
        self._savings_label.style().polish(self._savings_label)

    def _create_summary_card(
        self,
        title: str,
    ) -> tuple[QFrame, dict[str, QLabel]]:
        """Create one side of the before/after comparison."""
        card = QFrame(self)
        card.setObjectName("resultSummaryCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(9)

        title_label = QLabel(title, card)
        title_label.setObjectName("resultCardTitle")
        layout.addWidget(title_label)

        labels: dict[str, QLabel] = {}
        for key in ("format", "resolution", "size"):
            label = QLabel(card)
            label.setObjectName("resultMetric")
            labels[key] = label
            layout.addWidget(label)
        layout.addStretch()
        return card, labels
