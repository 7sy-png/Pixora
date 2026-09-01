"""Image processing settings panel."""

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
        form_layout.addRow(self._create_field_label("Ширина"), self.width_spin_box)

        self.height_spin_box = self._create_dimension_spin_box("heightSpinBox")
        form_layout.addRow(self._create_field_label("Высота"), self.height_spin_box)
        layout.addLayout(form_layout)

        self.keep_aspect_checkbox = QCheckBox("Сохранять пропорции", self)
        self.keep_aspect_checkbox.setObjectName("keepAspectCheckBox")
        self.keep_aspect_checkbox.setChecked(True)
        self.keep_aspect_checkbox.setEnabled(False)
        layout.addWidget(self.keep_aspect_checkbox)
        layout.addStretch()

    def set_image_info(self, image_info: ImageInfo) -> None:
        """Populate dimensions and enable controls for a selected image."""
        self.width_spin_box.setValue(image_info.width)
        self.height_spin_box.setValue(image_info.height)
        self.width_spin_box.setEnabled(True)
        self.height_spin_box.setEnabled(True)
        self.keep_aspect_checkbox.setEnabled(True)

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
