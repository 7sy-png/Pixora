"""Tests for the image-processing application service."""

from io import BytesIO

import pytest
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


def test_image_service_processes_uploaded_bytes() -> None:
    source_buffer = BytesIO()
    Image.new("RGB", (12, 8), "green").save(source_buffer, format="PNG")
    options = ProcessingOptions(6, 4, output_format="WEBP", quality=75)

    service = ImageService()
    result = service.process_bytes(
        source_buffer.getvalue(),
        options,
        filename="source.png",
    )
    encoded = service.encode(result, options)

    assert result.size == (6, 4)
    with Image.open(BytesIO(encoded)) as reopened:
        assert reopened.format == "WEBP"
        assert reopened.size == (6, 4)
    result.close()


def test_image_service_fits_batch_image_without_distorting_ratio() -> None:
    source_buffer = BytesIO()
    Image.new("RGB", (12, 12), "green").save(source_buffer, format="PNG")
    options = ProcessingOptions(
        600,
        400,
        keep_aspect_ratio=True,
        output_format="WEBP",
    )

    result = ImageService().process_bytes(
        source_buffer.getvalue(),
        options,
        filename="square.png",
        fit_within_bounds=True,
    )

    assert result.size == (400, 400)
    result.close()


def test_image_service_allows_exact_batch_dimensions_when_ratio_is_unlocked() -> None:
    source_buffer = BytesIO()
    Image.new("RGB", (12, 12), "green").save(source_buffer, format="PNG")
    options = ProcessingOptions(
        600,
        400,
        keep_aspect_ratio=False,
        output_format="WEBP",
    )

    result = ImageService().process_bytes(
        source_buffer.getvalue(),
        options,
        filename="square.png",
        fit_within_bounds=True,
    )

    assert result.size == (600, 400)
    result.close()


def test_image_service_saves_encoded_bytes_without_changes(tmp_path) -> None:
    destination = tmp_path / "result.webp"
    encoded_data = b"already-encoded-image"

    saved_path = ImageService().save_encoded(encoded_data, destination)

    assert saved_path == destination
    assert destination.read_bytes() == encoded_data


def test_image_service_reports_save_error_for_missing_directory(tmp_path) -> None:
    destination = tmp_path / "missing" / "result.png"

    with pytest.raises(OSError):
        ImageService().save_encoded(b"data", destination)
