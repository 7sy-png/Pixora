"""Main application window."""

from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PIL import Image
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

from app.ui.preview_widget import PreviewWidget
from app.ui.settings_panel import SettingsPanel
from app.services import ImageService


class MainWindow(QMainWindow):
    """Top-level window of the Pixora application."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pixora")
        self.setMinimumSize(960, 640)
        self.resize(1180, 760)
        self.image_service = ImageService()
        self.processed_image: Image.Image | None = None

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

    @Slot(str)
    def _handle_file_rejected(self, message: str) -> None:
        """Show a short validation message for an unsupported drop."""
        self.statusBar().showMessage(message, 5000)

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
        image_info = self.preview_widget.image_info
        if image_info is None:
            return

        try:
            processed_image = self.image_service.process(
                image_info.path,
                self.settings_panel.processing_options(),
            )
        except (OSError, ValueError) as error:
            self.statusBar().showMessage(str(error), 5000)
            return

        if self.processed_image is not None:
            self.processed_image.close()
        self.processed_image = processed_image
        self.statusBar().showMessage("Изображение успешно обработано")
