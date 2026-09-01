"""Capture reproducible Pixora screenshots for the project documentation."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw, ImageOps
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import Database
from app.models import ImageInfo, ProcessingResult
from app.repositories import HistoryRepository
from app.services import HistoryService, ImageService
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


def create_result(
    source: ImageInfo,
    *,
    output_format: str = "WEBP",
    output_width: int = 960,
    output_height: int = 540,
    output_size: int = 6_200,
    quality: int = 82,
) -> ProcessingResult:
    """Build result metadata used by the result and history screenshots."""
    return ProcessingResult(
        source=source,
        output_format=output_format,
        output_width=output_width,
        output_height=output_height,
        output_size=output_size,
        quality=quality,
    )


def main() -> int:
    """Render the main, result, and history states into PNG files."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    application = QApplication.instance() or QApplication([])
    apply_dark_theme(application)

    with TemporaryDirectory(prefix="pixora-screenshots-") as temporary_dir:
        temporary_path = Path(temporary_dir)
        sample_path = temporary_path / "aurora-demo.png"
        create_showcase_image(sample_path)

        history_service = HistoryService(
            HistoryRepository(Database(temporary_path / "pixora.db"))
        )
        window = MainWindow(ImageService(), history_service)
        window.resize(1180, 900)
        window.show()
        window.preview_widget.load_image(str(sample_path))
        window.settings_panel.width_spin_box.setValue(960)
        window.settings_panel.output_format_combo.setCurrentText("WEBP")
        window.settings_panel.quality_slider.setValue(82)
        window.toast.hide()
        application.processEvents()
        window.grab().save(str(SCREENSHOT_DIR / "pixora-main.png"))

        source = window.preview_widget.image_info
        if source is None:
            raise RuntimeError("The showcase image was not loaded")
        result = create_result(source)

        window.result_panel.set_result(result)
        window.result_panel.resize(640, 430)
        window.result_panel.show()
        application.processEvents()
        window.result_panel.grab().save(
            str(SCREENSHOT_DIR / "pixora-result.png")
        )
        window.result_panel.close()

        history_service.record_processing(
            result,
            temporary_path / "aurora-demo_pixora.webp",
        )
        second_source = ImageInfo(
            path=temporary_path / "mountain-landscape.jpg",
            filename="mountain-landscape.jpg",
            format="JPEG",
            width=2400,
            height=1600,
            size=1_820_000,
        )
        history_service.record_processing(
            create_result(
                second_source,
                output_width=1200,
                output_height=800,
                output_size=284_000,
                quality=76,
            ),
            temporary_path / "mountain-landscape_pixora.webp",
        )
        window.history_view.refresh()
        window.history_view.resize(1000, 520)
        window.history_view.show()
        application.processEvents()
        window.history_view.grab().save(
            str(SCREENSHOT_DIR / "pixora-history.png")
        )
        window.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
