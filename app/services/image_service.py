"""Application service for the image-processing pipeline."""

from dataclasses import replace
from io import BytesIO
from pathlib import Path

from PIL import Image

from app.models import ProcessingOptions
from app.processors import CompressProcessor, ProcessorFactory
from app.utils.validation import (
    validate_image_bytes,
    validate_image_file,
    validate_processing_options,
)


class ImageService:
    """Load an image and apply processing strategies in a stable order."""

    PIPELINE = ("resize", "rotate", "flip", "convert", "compress")

    def process(
        self,
        image_path: str | Path,
        options: ProcessingOptions,
    ) -> Image.Image:
        """Process a source file and return a detached Pillow image."""
        validate_processing_options(options)
        validated_path = validate_image_file(image_path)
        with Image.open(validated_path) as source_image:
            source_image.load()
            result = source_image.copy()

        return self._apply_pipeline(result, options)

    def process_bytes(
        self,
        data: bytes,
        options: ProcessingOptions,
        *,
        filename: str | None = None,
        fit_within_bounds: bool = False,
    ) -> Image.Image:
        """Process uploaded image bytes without writing a temporary file."""
        validate_processing_options(options)
        validate_image_bytes(data, filename=filename)
        with Image.open(BytesIO(data)) as source_image:
            source_image.load()
            result = source_image.copy()

        effective_options = options
        if fit_within_bounds and options.keep_aspect_ratio:
            width, height = self._fit_dimensions(
                result.size,
                (options.width, options.height),
            )
            effective_options = replace(options, width=width, height=height)

        return self._apply_pipeline(result, effective_options)

    @staticmethod
    def _fit_dimensions(
        source_size: tuple[int, int],
        bounds: tuple[int, int],
    ) -> tuple[int, int]:
        """Fit a source size into output bounds without changing its ratio."""
        source_width, source_height = source_size
        bound_width, bound_height = bounds
        scale = min(
            bound_width / source_width,
            bound_height / source_height,
        )
        return (
            max(1, round(source_width * scale)),
            max(1, round(source_height * scale)),
        )

    def _apply_pipeline(
        self,
        result: Image.Image,
        options: ProcessingOptions,
    ) -> Image.Image:
        """Apply the shared processor chain to a detached Pillow image."""

        try:
            for operation in self.PIPELINE:
                processor = ProcessorFactory.create(operation)
                next_result = processor.process(result, options)
                result.close()
                result = next_result
        except Exception:
            result.close()
            raise

        return result

    def encode(self, image: Image.Image, options: ProcessingOptions) -> bytes:
        """Encode a processed image using its output format and quality."""
        return CompressProcessor().encode(image, options)

    def save_encoded(self, data: bytes, destination: str | Path) -> Path:
        """Write already encoded result bytes without recompressing them."""
        destination_path = Path(destination)
        destination_path.write_bytes(data)
        return destination_path
