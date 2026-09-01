"""Validation rules shared by UI and processing services."""

import warnings
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.models import ProcessingOptions


SUPPORTED_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})
MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_DIMENSION = 50_000
MAX_OUTPUT_PIXELS = 100_000_000
SUPPORTED_OUTPUT_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})
SUPPORTED_ROTATIONS = frozenset({-90, 0, 90, 180})


class ImageValidationError(ValueError):
    """Raised when a selected source file cannot be processed safely."""


class ProcessingValidationError(ValueError):
    """Raised when processing options are outside supported limits."""


def validate_image_file(
    file_path: str | Path,
    *,
    verify_content: bool = True,
) -> Path:
    """Validate path, extension, size, and optionally image contents."""
    path = Path(file_path)
    if not path.is_file():
        raise ImageValidationError("Файл не найден")
    if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ImageValidationError("Поддерживаются только JPG, PNG и WEBP")

    try:
        file_size = path.stat().st_size
    except OSError as error:
        raise ImageValidationError("Не удалось прочитать информацию о файле") from error
    if file_size > MAX_IMAGE_SIZE_BYTES:
        raise ImageValidationError("Размер файла не должен превышать 20 МБ")

    if not verify_content:
        return path

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                image.verify()
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        SyntaxError,
    ) as error:
        raise ImageValidationError(
            "Файл повреждён или не является изображением"
        ) from error

    return path


def validate_processing_options(options: ProcessingOptions) -> None:
    """Validate dimensions and other settings before allocating image memory."""
    if not (
        1 <= options.width <= MAX_IMAGE_DIMENSION
        and 1 <= options.height <= MAX_IMAGE_DIMENSION
    ):
        raise ProcessingValidationError(
            f"Размеры должны быть от 1 до {MAX_IMAGE_DIMENSION} пикселей"
        )
    if options.width * options.height > MAX_OUTPUT_PIXELS:
        raise ProcessingValidationError(
            "Результат не должен превышать 100 миллионов пикселей"
        )

    output_format = options.output_format.strip().upper()
    if output_format == "JPG":
        output_format = "JPEG"
    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise ProcessingValidationError(
            f"Неподдерживаемый формат: {options.output_format}"
        )
    if not 1 <= options.quality <= 100:
        raise ProcessingValidationError("Качество должно быть в диапазоне от 1 до 100")
    if options.rotation not in SUPPORTED_ROTATIONS:
        raise ProcessingValidationError("Недопустимый угол поворота")
