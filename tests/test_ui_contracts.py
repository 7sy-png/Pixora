"""Regression tests for small but important interface contracts."""

import os
from pathlib import Path
import subprocess
import sys

from PIL import Image

from app.ui.theme import (
    APP_ICON_PATH,
    LOGO_PATH,
    SPIN_DOWN_ICON_PATH,
    SPIN_UP_ICON_PATH,
    load_dark_stylesheet,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_branding_assets_are_valid() -> None:
    """Keep the generated logo and multi-size Windows icon packaged."""
    assert LOGO_PATH.is_file()
    assert APP_ICON_PATH.is_file()
    assert SPIN_UP_ICON_PATH.is_file()
    assert SPIN_DOWN_ICON_PATH.is_file()

    stylesheet = load_dark_stylesheet()
    assert "__SPIN_UP_ICON__" not in stylesheet
    assert "__SPIN_DOWN_ICON__" not in stylesheet
    assert SPIN_UP_ICON_PATH.as_posix() in stylesheet
    assert SPIN_DOWN_ICON_PATH.as_posix() in stylesheet

    with Image.open(LOGO_PATH) as logo:
        assert logo.size == (512, 512)
        assert logo.mode == "RGBA"

    with Image.open(APP_ICON_PATH) as icon:
        assert icon.format == "ICO"
        assert icon.info["sizes"] >= {(16, 16), (32, 32), (256, 256)}


def test_png_replaces_quality_slider_with_lossless_hint() -> None:
    """Exercise Qt widgets in an isolated offscreen application process."""
    script = """
from pathlib import Path
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QApplication
from app.models import ImageInfo
from app.ui.preview_widget import PreviewWidget
from app.ui.settings_panel import SettingsPanel

application = QApplication([])
panel = SettingsPanel()
panel.set_image_info(ImageInfo(Path('image.png'), 'image.png', 'PNG', 16, 9, 64))
assert panel.output_format_combo.currentText() == 'PNG'
assert panel.quality_controls.isHidden()
assert not panel.lossless_hint.isHidden()

panel.output_format_combo.setCurrentText('WEBP')
assert not panel.quality_controls.isHidden()
assert panel.lossless_hint.isHidden()
assert panel.quality_slider.isEnabled()
panel.quality_slider.setValue(67)
assert panel.quality_value_label.text() == '67'

transforms = []
panel.preview_transform_changed.connect(lambda *values: transforms.append(values))
panel.rotation_buttons[90].click()
assert panel.rotation == 90
assert transforms[-1] == (90, False, False)
panel.flip_horizontal_button.click()
assert transforms[-1] == (90, True, False)

panel.width_spin_box.setValue(1600)
panel.aspect_preset_buttons['16:9'].click()
assert panel.keep_aspect_checkbox.isChecked()
assert panel.height_spin_box.value() == 900
panel.aspect_preset_buttons['1:1'].click()
assert panel.height_spin_box.value() == 1600

preview = PreviewWidget()
image = QImage(2, 3, QImage.Format.Format_RGB32)
for y in range(3):
    for x in range(2):
        image.setPixelColor(x, y, QColor(y * 2 + x + 1, 0, 0))
preview._source_pixmap = QPixmap.fromImage(image)

preview.set_transform(90, False, False)
rotated = preview._transformed_pixmap().toImage()
assert (rotated.width(), rotated.height()) == (3, 2)
assert [rotated.pixelColor(x, 0).red() for x in range(3)] == [5, 3, 1]

preview.set_transform(0, True, False)
reflected = preview._transformed_pixmap().toImage()
assert [reflected.pixelColor(x, 0).red() for x in range(2)] == [2, 1]
"""
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        timeout=20,
    )
