"""Main application window."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    """Top-level window of the Pixora application."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pixora")
        self.setMinimumSize(960, 640)
        self.resize(1180, 760)

        self._build_interface()

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

        for title, object_name in (
            ("История", "historyButton"),
            ("Настройки", "settingsButton"),
        ):
            button = QPushButton(title, header)
            button.setObjectName(object_name)
            button.setFlat(True)
            layout.addWidget(button)

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
        """Create an empty image preview area."""
        preview_card = QFrame(self)
        preview_card.setObjectName("previewCard")
        preview_card.setFrameShape(QFrame.Shape.StyledPanel)
        preview_card.setMinimumHeight(420)
        preview_card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        layout = QVBoxLayout(preview_card)
        placeholder = QLabel("Предпросмотр изображения", preview_card)
        placeholder.setObjectName("previewPlaceholder")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder)
        return preview_card

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

        placeholder = QLabel(
            "Параметры обработки появятся здесь после загрузки изображения.",
            settings_card,
        )
        placeholder.setObjectName("settingsPlaceholder")
        placeholder.setWordWrap(True)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(placeholder)
        layout.addStretch()
        return settings_card
