"""Image compression and serialization strategy."""

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from PIL import Image

from app.models import ProcessingOptions
from app.processors.base import ImageProcessor


class CompressProcessor(ImageProcessor):
    """Apply format-specific compression when a Pillow image is serialized."""

    SUPPORTED_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})

    def process(
        self,
        image: Image.Image,
        options: ProcessingOptions,
    ) -> Image.Image:
        """Validate compression settings and return an independent image copy."""
        self._normalized_format(options)
        self._validate_quality(options.quality)
        return image.copy()

    def save(
        self,
        image: Image.Image,
        destination: str | Path | BinaryIO,
        options: ProcessingOptions,
    ) -> None:
        """Save an image using compression settings for its output format."""
        output_format = self._normalized_format(options)
        save_options = self._save_options(output_format, options.quality)
        image.save(destination, format=output_format, **save_options)

    def encode(self, image: Image.Image, options: ProcessingOptions) -> bytes:
        """Serialize an image to bytes using the configured quality."""
        buffer = BytesIO()
        self.save(image, buffer, options)
        return buffer.getvalue()

    def _normalized_format(self, options: ProcessingOptions) -> str:
        """Normalize and validate the requested output format."""
        output_format = options.output_format.strip().upper()
        if output_format == "JPG":
            output_format = "JPEG"
        if output_format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Неподдерживаемый формат: {options.output_format}")
        return output_format

    def _save_options(
        self,
        output_format: str,
        quality: int,
    ) -> dict[str, int | bool]:
        """Build Pillow keyword arguments for the selected format."""
        self._validate_quality(quality)
        if output_format == "JPEG":
            return {"quality": quality, "optimize": True}
        if output_format == "WEBP":
            return {"quality": quality, "method": 6}
        return {"optimize": True}

    @staticmethod
    def _validate_quality(quality: int) -> None:
        """Ensure quality matches the range exposed by the UI."""
        if not 1 <= quality <= 100:
            raise ValueError("Качество должно быть в диапазоне от 1 до 100")
