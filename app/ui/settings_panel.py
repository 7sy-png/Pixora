"""Image processing settings panel."""

from PySide6.QtCore import QSignalBlocker, Slot

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLabel,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.models import ImageInfo


class SettingsPanel(QWidget):
    """Display editable output dimensions for the selected image."""

    MAX_DIMENSION = 100_000

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsPanel")
        self._aspect_ratio: float | None = None

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
        layout.addStretch()

    def set_image_info(self, image_info: ImageInfo) -> None:
        """Populate dimensions and enable controls for a selected image."""
        self._aspect_ratio = image_info.width / image_info.height
        with (
            QSignalBlocker(self.width_spin_box),
            QSignalBlocker(self.height_spin_box),
        ):
            self.width_spin_box.setValue(image_info.width)
            self.height_spin_box.setValue(image_info.height)

        self.width_spin_box.setEnabled(True)
        self.height_spin_box.setEnabled(True)
        self.keep_aspect_checkbox.setEnabled(True)

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
