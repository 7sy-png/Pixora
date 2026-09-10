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
from tempfile import TemporaryDirectory
from PIL import Image as PillowImage
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QApplication
from app.models import ImageInfo
from app.ui.preview_widget import PreviewWidget
from app.ui.batch_panel import BatchPanel
from app.ui.settings_panel import SettingsPanel
from app.ui.theme import apply_dark_theme

application = QApplication([])
apply_dark_theme(application)
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

dimensions = []
panel.preview_dimensions_changed.connect(lambda *values: dimensions.append(values))
panel.width_spin_box.setValue(1600)
panel.aspect_preset_buttons['16:9'].click()
assert panel.keep_aspect_checkbox.isChecked()
assert panel.height_spin_box.value() == 900
assert dimensions[-1] == (1600, 900)
panel.aspect_preset_buttons['1:1'].click()
assert panel.height_spin_box.value() == 1600
panel.restore_aspect_button.click()
assert panel.aspect_preset_group.checkedButton() is None
assert panel.keep_aspect_checkbox.isChecked()
assert (panel.width_spin_box.value(), panel.height_spin_box.value()) == (16, 9)
assert dimensions[-1] == (16, 9)

temporary_directory = TemporaryDirectory()
first_batch_path = Path(temporary_directory.name) / 'first.png'
second_batch_path = Path(temporary_directory.name) / 'second.png'
PillowImage.new('RGB', (16, 9), 'red').save(first_batch_path)
PillowImage.new('RGB', (16, 9), 'blue').save(second_batch_path)
batch = BatchPanel()
batch.set_files([
    first_batch_path,
    second_batch_path,
])
assert batch.file_list.count() == 2
assert batch.settings_panel.process_button.text() == 'Запустить обработку'
assert batch.clear_files_button.isEnabled()
batch.set_processing(True)
assert batch.cancel_button.isEnabled()
batch.set_processing(False)
batch.set_batch_created({'jobs': [
    {'job_id': 'job-1'},
    {'job_id': 'job-2'},
]})
batch.finish_batch({
    'total': 2,
    'completed': 2,
    'failed': 0,
    'progress': 100,
    'jobs': [
        {
            'job_id': 'job-1',
            'filename': 'first.png',
            'status': 'SUCCESS',
            'progress': 100,
            'worker': 'worker@node-a',
            'output': {'filename': 'pixora-main_pixora.webp'},
        },
        {
            'job_id': 'job-2',
            'filename': 'second.png',
            'status': 'SUCCESS',
            'progress': 100,
            'worker': 'worker@node-b',
            'output': {'filename': 'pixora-result_pixora.webp'},
        },
    ],
})
assert batch.progress_bar.value() == 100
assert batch.save_button.isEnabled()
assert 'worker@node-a' in batch.file_list.item(0).text()
assert 'worker@node-b' in batch.file_list.item(1).text()
batch.clear_files()
assert batch.file_list.count() == 0
assert not batch.settings_panel.process_button.isEnabled()
temporary_directory.cleanup()

panel.show()
panel.output_format_combo.showPopup()
application.processEvents()
popup_view = panel.output_format_combo.view()
assert popup_view.geometry().top() == 0
assert popup_view.height() == popup_view.window().height()
panel.output_format_combo.hidePopup()

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

preview.set_transform(0, False, False)
preview.set_output_size(16, 9)
resized = preview._transformed_pixmap().toImage()
assert (resized.width(), resized.height()) == (16, 9)
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
