"""Image processing settings panel."""

from PySide6.QtCore import QSignalBlocker, Qt, Signal, Slot

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSlider,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.models import ImageInfo, ProcessingOptions


class SettingsPanel(QWidget):
    """Display editable output dimensions for the selected image."""

    MAX_DIMENSION = 100_000
    processing_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsPanel")
        self._aspect_ratio: float | None = None
        self._rotation = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        section_label = QLabel("Размер", self)
        section_label.setObjectName("sectionLabel")
        layout.addWidget(section_label)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setHorizontalSpacing(14)
        form_layout.setVerticalSpacing(10)
        form_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )

        self.width_spin_box = self._create_dimension_spin_box("widthSpinBox")
        self.width_spin_box.valueChanged.connect(self._on_width_changed)
        form_layout.addRow(self._create_field_label("Ширина"), self.width_spin_box)

        self.height_spin_box = self._create_dimension_spin_box("heightSpinBox")
        self.height_spin_box.valueChanged.connect(self._on_height_changed)
        form_layout.addRow(self._create_field_label("Высота"), self.height_spin_box)
        layout.addLayout(form_layout)

        self.keep_aspect_checkbox = QCheckBox("Сохранять пропорции", self)
        self.keep_aspect_checkbox.setObjectName("keepAspectCheckBox")
        self.keep_aspect_checkbox.setChecked(True)
        self.keep_aspect_checkbox.setEnabled(False)
        self.keep_aspect_checkbox.toggled.connect(self._on_keep_aspect_toggled)
        layout.addWidget(self.keep_aspect_checkbox)

        format_label = QLabel("Формат", self)
        format_label.setObjectName("sectionLabel")
        layout.addWidget(format_label)

        self.output_format_combo = QComboBox(self)
        self.output_format_combo.setObjectName("outputFormatCombo")
        self.output_format_combo.addItems(("JPEG", "PNG", "WEBP"))
        self.output_format_combo.setEnabled(False)
        self.output_format_combo.currentTextChanged.connect(
            self._update_quality_state
        )
        layout.addWidget(self.output_format_combo)

        quality_header = QHBoxLayout()
        quality_header.setContentsMargins(0, 0, 0, 0)

        quality_label = QLabel("Качество", self)
        quality_label.setObjectName("sectionLabel")
        quality_header.addWidget(quality_label)
        quality_header.addStretch()

        self.quality_value_label = QLabel("80", self)
        self.quality_value_label.setObjectName("qualityValue")
        quality_header.addWidget(self.quality_value_label)
        layout.addLayout(quality_header)

        self.quality_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.quality_slider.setObjectName("qualitySlider")
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(80)
        self.quality_slider.setEnabled(False)
        self.quality_slider.valueChanged.connect(self._on_quality_changed)
        layout.addWidget(self.quality_slider)

        rotation_label = QLabel("Поворот", self)
        rotation_label.setObjectName("sectionLabel")
        layout.addWidget(rotation_label)

        rotation_layout = QHBoxLayout()
        rotation_layout.setContentsMargins(0, 0, 0, 0)
        rotation_layout.setSpacing(8)
        self.rotation_buttons: dict[int, QPushButton] = {}
        for angle, text in ((-90, "−90°"), (90, "+90°"), (180, "180°")):
            button = QPushButton(text, self)
            button.setObjectName("toolButton")
            button.setCheckable(True)
            button.setEnabled(False)
            button.clicked.connect(
                lambda checked, value=angle: self._select_rotation(value, checked)
            )
            self.rotation_buttons[angle] = button
            rotation_layout.addWidget(button)
        layout.addLayout(rotation_layout)

        flip_label = QLabel("Отражение", self)
        flip_label.setObjectName("sectionLabel")
        layout.addWidget(flip_label)

        self.flip_horizontal_button = QPushButton("↔  По горизонтали", self)
        self.flip_horizontal_button.setObjectName("toolButton")
        self.flip_horizontal_button.setCheckable(True)
        self.flip_horizontal_button.setEnabled(False)
        layout.addWidget(self.flip_horizontal_button)

        self.flip_vertical_button = QPushButton("↕  По вертикали", self)
        self.flip_vertical_button.setObjectName("toolButton")
        self.flip_vertical_button.setCheckable(True)
        self.flip_vertical_button.setEnabled(False)
        layout.addWidget(self.flip_vertical_button)
        layout.addStretch()

        self.process_button = QPushButton("Обработать изображение", self)
        self.process_button.setObjectName("processButton")
        self.process_button.setEnabled(False)
        self.process_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.process_button.clicked.connect(self.processing_requested)
        layout.addWidget(self.process_button)

        self.processing_indicator = QProgressBar(self)
        self.processing_indicator.setObjectName("processingIndicator")
        self.processing_indicator.setRange(0, 0)
        self.processing_indicator.setTextVisible(False)
        self.processing_indicator.setFixedHeight(4)
        self.processing_indicator.hide()
        layout.addWidget(self.processing_indicator)

    def set_image_info(self, image_info: ImageInfo) -> None:
        """Populate dimensions and enable controls for a selected image."""
        self._aspect_ratio = image_info.width / image_info.height
        self._rotation = 0
        with (
            QSignalBlocker(self.width_spin_box),
            QSignalBlocker(self.height_spin_box),
        ):
            self.width_spin_box.setValue(image_info.width)
            self.height_spin_box.setValue(image_info.height)

        self.width_spin_box.setEnabled(True)
        self.height_spin_box.setEnabled(True)
        self.keep_aspect_checkbox.setEnabled(True)
        self.output_format_combo.setCurrentText(image_info.format)
        self.output_format_combo.setEnabled(True)
        self._update_quality_state(self.output_format_combo.currentText())
        for button in self.rotation_buttons.values():
            with QSignalBlocker(button):
                button.setChecked(False)
            button.setEnabled(True)
        for button in (self.flip_horizontal_button, self.flip_vertical_button):
            with QSignalBlocker(button):
                button.setChecked(False)
            button.setEnabled(True)
        self.process_button.setEnabled(True)

    @property
    def rotation(self) -> int:
        """Return the currently selected clockwise/counter-clockwise angle."""
        return self._rotation

    @property
    def flip_horizontal(self) -> bool:
        """Return whether horizontal reflection is selected."""
        return self.flip_horizontal_button.isChecked()

    @property
    def flip_vertical(self) -> bool:
        """Return whether vertical reflection is selected."""
        return self.flip_vertical_button.isChecked()

    def processing_options(self) -> ProcessingOptions:
        """Build a standalone snapshot of all currently visible settings."""
        return ProcessingOptions(
            width=self.width_spin_box.value(),
            height=self.height_spin_box.value(),
            keep_aspect_ratio=self.keep_aspect_checkbox.isChecked(),
            output_format=self.output_format_combo.currentText(),
            quality=self.quality_slider.value(),
            rotation=self.rotation,
            flip_horizontal=self.flip_horizontal,
            flip_vertical=self.flip_vertical,
        )

    def set_processing(self, is_processing: bool) -> None:
        """Toggle the button and indeterminate progress state."""
        self.process_button.setEnabled(
            not is_processing and self.width_spin_box.isEnabled()
        )
        self.process_button.setText(
            "Обработка..." if is_processing else "Обработать изображение"
        )
        self.processing_indicator.setVisible(is_processing)

    @Slot(int)
    def _on_width_changed(self, width: int) -> None:
        """Recalculate height while preserving the source aspect ratio."""
        if not self.keep_aspect_checkbox.isChecked() or self._aspect_ratio is None:
            return

        height = max(1, round(width / self._aspect_ratio))
        with QSignalBlocker(self.height_spin_box):
            self.height_spin_box.setValue(height)

    @Slot(int)
    def _on_height_changed(self, height: int) -> None:
        """Recalculate width while preserving the source aspect ratio."""
        if not self.keep_aspect_checkbox.isChecked() or self._aspect_ratio is None:
            return

        width = max(1, round(height * self._aspect_ratio))
        with QSignalBlocker(self.width_spin_box):
            self.width_spin_box.setValue(width)

    @Slot(bool)
    def _on_keep_aspect_toggled(self, is_checked: bool) -> None:
        """Restore matching dimensions when aspect locking is enabled."""
        if is_checked:
            self._on_width_changed(self.width_spin_box.value())

    @Slot(str)
    def _update_quality_state(self, output_format: str) -> None:
        """Disable quality controls for lossless PNG output."""
        is_available = self.output_format_combo.isEnabled() and output_format != "PNG"
        self.quality_slider.setEnabled(is_available)
        self.quality_value_label.setEnabled(is_available)
        self.quality_value_label.setText(
            str(self.quality_slider.value()) if is_available else "—"
        )

    @Slot(int)
    def _on_quality_changed(self, quality: int) -> None:
        """Keep the numeric quality indicator in sync with the slider."""
        if self.quality_slider.isEnabled():
            self.quality_value_label.setText(str(quality))

    def _select_rotation(self, angle: int, is_checked: bool) -> None:
        """Select one rotation button or reset rotation when toggled off."""
        self._rotation = angle if is_checked else 0
        if not is_checked:
            return

        for other_angle, button in self.rotation_buttons.items():
            if other_angle == angle:
                continue
            with QSignalBlocker(button):
                button.setChecked(False)

    def _create_dimension_spin_box(self, object_name: str) -> QSpinBox:
        """Create a consistently configured pixel dimension field."""
        spin_box = QSpinBox(self)
        spin_box.setObjectName(object_name)
        spin_box.setRange(1, self.MAX_DIMENSION)
        spin_box.setSuffix(" px")
        spin_box.setEnabled(False)
        spin_box.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        return spin_box

    def _create_field_label(self, text: str) -> QLabel:
        """Create a form label with the shared field style."""
        label = QLabel(text, self)
        label.setObjectName("fieldLabel")
        return label
