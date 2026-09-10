"""Capture reproducible Pixora screenshots for the project documentation."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import monotonic

from PIL import Image, ImageDraw, ImageOps
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models import ProcessingOptions, ProcessingResult
from app.services import ImageService
from app.ui.main_window import MainWindow
from app.ui.theme import apply_dark_theme


SCREENSHOT_DIR = PROJECT_ROOT / "docs" / "screenshots"


def create_showcase_image(destination: Path) -> None:
    """Create a deterministic sample image for the preview screenshot."""
    gradient = Image.linear_gradient("L").resize((1280, 720))
    image = ImageOps.colorize(gradient, "#111827", "#6d4ed4").convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    draw.ellipse((760, 80, 1220, 540), fill=(135, 112, 255, 80))
    draw.ellipse((70, 310, 570, 810), fill=(34, 211, 238, 55))
    draw.rounded_rectangle(
        (170, 135, 745, 500),
        radius=48,
        fill=(9, 13, 20, 135),
        outline=(183, 167, 255, 150),
        width=3,
    )
    draw.line((220, 425, 390, 260, 520, 370, 690, 190), fill="#b7a7ff", width=8)
    image.save(destination, format="PNG", optimize=True)


def main() -> int:
    """Render workspace, result and distributed batch states into PNG files."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    application = QApplication.instance() or QApplication([])
    apply_dark_theme(application)

    with TemporaryDirectory(prefix="pixora-screenshots-") as temporary_dir:
        temporary_path = Path(temporary_dir)
        sample_path = temporary_path / "aurora-demo.png"
        create_showcase_image(sample_path)

        image_service = ImageService()
        window = MainWindow(image_service)
        window.resize(1180, 760)
        window.show()
        window.preview_widget.load_image(str(sample_path))
        window.settings_panel.width_spin_box.setValue(960)
        window.settings_panel.aspect_preset_buttons["1:1"].click()
        window.settings_panel.output_format_combo.setCurrentText("WEBP")
        window.settings_panel.quality_slider.setValue(82)
        application.processEvents()
        window.grab().save(str(SCREENSHOT_DIR / "pixora-main.png"))

        source = window.preview_widget.image_info
        if source is None:
            raise RuntimeError("The showcase image was not loaded")
        options = ProcessingOptions(
            width=960,
            height=540,
            output_format="WEBP",
            quality=82,
        )
        processed_image = image_service.process(sample_path, options)
        encoded_data = image_service.encode(processed_image, options)
        result = ProcessingResult(
            source=source,
            output_format="WEBP",
            output_width=processed_image.width,
            output_height=processed_image.height,
            output_size=len(encoded_data),
            quality=82,
        )
        window.result_panel.set_result(result, encoded_data)
        window.content_stack.setCurrentWidget(window.result_panel)
        application.processEvents()
        window.grab().save(str(SCREENSHOT_DIR / "pixora-result.png"))

        batch_sources = [sample_path]
        for index, size in enumerate(((900, 900), (800, 1200)), start=2):
            batch_source = temporary_path / f"aurora-demo-{index}.png"
            Image.new(
                "RGB",
                size,
                (45 + index * 35, 55, 130 + index * 20),
            ).save(batch_source, format="PNG")
            batch_sources.append(batch_source)
        window.batch_panel.set_files(batch_sources)
        window.batch_panel.set_batch_created(
            {
                "jobs": [
                    {"job_id": "job-1"},
                    {"job_id": "job-2"},
                    {"job_id": "job-3"},
                ]
            }
        )
        window.batch_panel.set_processing(True)
        window.batch_panel._started_at = monotonic() - 2.4
        window.batch_panel.update_cluster_status(
            {
                "api": "online",
                "redis": "online",
                "minio": "online",
                "queue_depth": 1,
                "workers": [
                    {
                        "worker_id": "worker@container-a",
                        "status": "busy",
                        "active_tasks": 1,
                        "active_job_ids": ["job-2"],
                    },
                    {
                        "worker_id": "worker@container-b",
                        "status": "busy",
                        "active_tasks": 1,
                        "active_job_ids": ["job-3"],
                    },
                ],
            }
        )
        window.batch_panel.update_batch_status(
            {
                "total": 3,
                "pending": 0,
                "processing": 2,
                "completed": 1,
                "failed": 0,
                "cancelled": 0,
                "progress": 55,
                "jobs": [
                    {
                        "job_id": "job-1",
                        "filename": "aurora-demo.png",
                        "status": "SUCCESS",
                        "progress": 100,
                        "worker": "worker@container-a",
                    },
                    {
                        "job_id": "job-2",
                        "filename": "aurora-demo-2.png",
                        "status": "PROCESSING",
                        "progress": 45,
                        "worker": "worker@container-a",
                    },
                    {
                        "job_id": "job-3",
                        "filename": "aurora-demo-3.png",
                        "status": "PROCESSING",
                        "progress": 20,
                        "worker": "worker@container-b",
                    },
                ],
            }
        )
        window.content_stack.setCurrentWidget(window.batch_panel)
        window.batch_mode_button.setText("Обычный режим")
        application.processEvents()
        window.grab().save(str(SCREENSHOT_DIR / "pixora-batch.png"))

        processed_image.close()
        window.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
