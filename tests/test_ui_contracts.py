"""Regression tests for small but important interface contracts."""

import os
from pathlib import Path
import subprocess
import sys

from PIL import Image

from app.ui.theme import APP_ICON_PATH, LOGO_PATH


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_branding_assets_are_valid() -> None:
    """Keep the generated logo and multi-size Windows icon packaged."""
    assert LOGO_PATH.is_file()
    assert APP_ICON_PATH.is_file()

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
from PySide6.QtWidgets import QApplication
from app.models import ImageInfo
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
