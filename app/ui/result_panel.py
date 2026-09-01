"""Inline panel that presents a completed image-processing result."""

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QPixmap, QResizeEvent, QShowEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.models import ProcessingResult
from app.utils.file_utils import format_file_size


class ResultPanel(QWidget):
    """Show the processed image and its metadata inside the main window."""

    save_requested = Signal()
    back_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("resultPanel")
        self._source_pixmap = QPixmap()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(18)

        heading_layout = QVBoxLayout()
        heading_layout.setSpacing(4)
        title_label = QLabel("Готово", self)
        title_label.setObjectName("resultTitle")
        heading_layout.addWidget(title_label)

        subtitle_label = QLabel(
            "Проверьте результат и сохраните изображение",
            self,
        )
        subtitle_label.setObjectName("resultSubtitle")
        heading_layout.addWidget(subtitle_label)
        layout.addLayout(heading_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        content_layout.addWidget(self._create_preview_card(), stretch=3)
        content_layout.addWidget(self._create_details_card(), stretch=2)
        layout.addLayout(content_layout, stretch=1)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        self._status_label = QLabel(self)
        self._status_label.setObjectName("resultStatus")
        self._status_label.hide()
        actions_layout.addWidget(self._status_label, stretch=1)

        back_button = QPushButton("Вернуться к настройкам", self)
        back_button.setObjectName("secondaryButton")
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        back_button.clicked.connect(self.back_requested)
        actions_layout.addWidget(back_button)

        self.save_button = QPushButton("Сохранить изображение", self)
        self.save_button.setObjectName("saveResultButton")
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.clicked.connect(self.save_requested)
        actions_layout.addWidget(self.save_button)
        layout.addLayout(actions_layout)

    def set_result(self, result: ProcessingResult, encoded_data: bytes) -> None:
        """Populate the preview, comparison cards, and savings message."""
        pixmap = QPixmap()
        pixmap.loadFromData(encoded_data)
        self._source_pixmap = pixmap
        self._update_scaled_pixmap()
        QTimer.singleShot(0, self._update_scaled_pixmap)

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
        self.clear_status()

    def show_status(self, message: str, kind: str = "success") -> None:
        """Display non-overlapping save feedback in the action row."""
        self._status_label.setProperty("kind", kind)
        self._status_label.setText(message)
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)
        self._status_label.show()

    def clear_status(self) -> None:
        """Hide feedback from the previous result or save attempt."""
        self._status_label.clear()
        self._status_label.hide()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Keep the inline preview fitted to the available area."""
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def showEvent(self, event: QShowEvent) -> None:
        """Refresh the preview after the result page receives its layout."""
        super().showEvent(event)
        QTimer.singleShot(0, self._update_scaled_pixmap)

    def _create_preview_card(self) -> QFrame:
        """Create the large output preview area."""
        card = QFrame(self)
        card.setObjectName("resultPreviewCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)

        self._preview_label = QLabel(card)
        self._preview_label.setObjectName("resultPreviewImage")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored,
        )
        layout.addWidget(self._preview_label)
        return card

    def _create_details_card(self) -> QFrame:
        """Create before/after metadata and the savings summary."""
        card = QFrame(self)
        card.setObjectName("resultDetailsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        source_card, self._source_labels = self._create_summary_card("Исходник")
        output_card, self._output_labels = self._create_summary_card("Результат")
        layout.addWidget(source_card)
        layout.addWidget(output_card)

        self._savings_label = QLabel(card)
        self._savings_label.setObjectName("savingsLabel")
        self._savings_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._savings_label)
        layout.addStretch()
        return card

    def _create_summary_card(
        self,
        title: str,
    ) -> tuple[QFrame, dict[str, QLabel]]:
        """Create one compact side of the before/after comparison."""
        card = QFrame(self)
        card.setObjectName("resultSummaryCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(7)

        title_label = QLabel(title, card)
        title_label.setObjectName("resultCardTitle")
        layout.addWidget(title_label)

        labels: dict[str, QLabel] = {}
        for key in ("format", "resolution", "size"):
            label = QLabel(card)
            label.setObjectName("resultMetric")
            labels[key] = label
            layout.addWidget(label)
        return card, labels

    def _update_scaled_pixmap(self) -> None:
        """Scale the encoded output without changing its aspect ratio."""
        if self._source_pixmap.isNull():
            return
        target_size = self._preview_label.size().boundedTo(
            self._source_pixmap.size()
        )
        self._preview_label.setPixmap(
            self._source_pixmap.scaled(
                target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
