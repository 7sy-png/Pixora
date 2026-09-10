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
from app.services import ImageService
from app.ui.preview_widget import PreviewWidget
from app.ui.batch_panel import BatchPanel
from app.ui.main_window import MainWindow
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
assert not batch.settings_panel.output_format_combo.isEnabled()
assert not batch.settings_panel.quality_slider.isEnabled()
assert not batch.settings_panel.format_unavailable_hint.isHidden()
assert batch.clear_files_button.isEnabled()
batch.set_processing(True)
assert batch.cancel_button.isEnabled()
batch.set_processing(False)
batch.set_batch_created({'jobs': [
    {'job_id': 'job-1'},
    {'job_id': 'job-2'},
]})
batch.update_cluster_status({
    'api': 'online',
    'redis': 'online',
    'minio': 'online',
    'queue_depth': 2,
    'workers': [
        {
            'worker_id': 'worker@node-a',
            'status': 'idle',
            'active_tasks': 0,
            'active_job_ids': [],
        },
        {
            'worker_id': 'worker@node-b',
            'status': 'idle',
            'active_tasks': 0,
            'active_job_ids': [],
        },
    ],
})
assert batch.api_node.property('state') == 'online'
assert batch.redis_node.detail_label.text() == 'В очереди: 2'
assert len(batch._worker_nodes) == 2
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
assert 'Worker 1' in batch.file_list.item(0).text()
assert 'Worker 2' in batch.file_list.item(1).text()
assert 'worker@node-a' in batch.file_list.item(0).toolTip()
assert 'Worker 1 — 1' in batch.distribution_label.text()
assert 'Worker 2 — 1' in batch.distribution_label.text()
batch.clear_files()
assert batch.file_list.count() == 0
assert not batch.settings_panel.process_button.isEnabled()

main_window = MainWindow(ImageService())
main_window.preview_widget.load_image(str(first_batch_path))
assert main_window.preview_widget.image_info is not None
assert main_window.settings_panel.process_button.isEnabled()
assert main_window.preview_widget.clear_image_button.isEnabled()
main_window.preview_widget.clear_image_button.click()
assert main_window.preview_widget.image_info is None
assert not main_window.settings_panel.process_button.isEnabled()
assert main_window.preview_widget._stack.currentWidget() is main_window.preview_widget.drop_zone
assert main_window.statusBar().currentMessage() == 'Готово к работе'
main_window.close()
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
