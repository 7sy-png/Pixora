"""Tests for the image-processing application service."""

from io import BytesIO

from PIL import Image

from app.models import ProcessingOptions
from app.services import ImageService


def test_image_service_runs_processing_pipeline(tmp_path) -> None:
    source_path = tmp_path / "source.png"
    Image.new("RGBA", (8, 6), (255, 0, 0, 128)).save(source_path)
    options = ProcessingOptions(
        width=4,
        height=3,
        output_format="JPEG",
        quality=70,
        rotation=90,
        flip_horizontal=True,
    )

    service = ImageService()
    result = service.process(source_path, options)

    assert result.size == (3, 4)
    assert result.mode == "RGB"

    encoded = service.encode(result, options)
    with Image.open(BytesIO(encoded)) as reopened:
        assert reopened.format == "JPEG"
        assert reopened.size == (3, 4)

    result.close()


def test_image_service_does_not_modify_source_file(tmp_path) -> None:
    source_path = tmp_path / "source.webp"
    Image.new("RGB", (12, 10), "blue").save(source_path)
    original_bytes = source_path.read_bytes()

    result = ImageService().process(
        source_path,
        ProcessingOptions(6, 5, output_format="WEBP"),
    )

    assert source_path.read_bytes() == original_bytes
    result.close()
