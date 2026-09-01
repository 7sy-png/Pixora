"""Tests for shared image and processing validation."""

import pytest
from PIL import Image

from app.models import ProcessingOptions
from app.utils.validation import (
    MAX_IMAGE_SIZE_BYTES,
    ImageValidationError,
    ProcessingValidationError,
    validate_image_file,
    validate_processing_options,
)


def test_validate_image_file_accepts_supported_image(tmp_path) -> None:
    image_path = tmp_path / "valid.png"
    Image.new("RGB", (20, 10), "red").save(image_path)

    assert validate_image_file(image_path) == image_path


def test_validate_image_file_rejects_wrong_extension(tmp_path) -> None:
    file_path = tmp_path / "document.txt"
    file_path.write_text("not an image", encoding="utf-8")

    with pytest.raises(ImageValidationError, match="только JPG"):
        validate_image_file(file_path)


def test_validate_image_file_rejects_missing_file(tmp_path) -> None:
    with pytest.raises(ImageValidationError, match="не найден"):
        validate_image_file(tmp_path / "missing.png")


def test_validate_image_file_rejects_corrupted_image(tmp_path) -> None:
    file_path = tmp_path / "broken.png"
    file_path.write_bytes(b"not a real png")

    with pytest.raises(ImageValidationError, match="повреждён"):
        validate_image_file(file_path)


def test_validate_image_file_rejects_file_larger_than_20_mb(tmp_path) -> None:
    file_path = tmp_path / "huge.png"
    with file_path.open("wb") as file:
        file.seek(MAX_IMAGE_SIZE_BYTES)
        file.write(b"0")

    with pytest.raises(ImageValidationError, match="20 МБ"):
        validate_image_file(file_path, verify_content=False)


@pytest.mark.parametrize(
    "options",
    [
        ProcessingOptions(0, 100),
        ProcessingOptions(100, 0),
        ProcessingOptions(20_000, 20_000),
        ProcessingOptions(100, 100, quality=101),
        ProcessingOptions(100, 100, rotation=45),
    ],
)
def test_validate_processing_options_rejects_invalid_values(
    options: ProcessingOptions,
) -> None:
    with pytest.raises(ProcessingValidationError):
        validate_processing_options(options)


def test_validate_processing_options_accepts_jpg_alias() -> None:
    validate_processing_options(
        ProcessingOptions(100, 50, output_format="jpg", quality=1)
    )
