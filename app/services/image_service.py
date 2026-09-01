"""Application service for the image-processing pipeline."""

from pathlib import Path

from PIL import Image

from app.models import ProcessingOptions
from app.processors import CompressProcessor, ProcessorFactory


class ImageService:
    """Load an image and apply processing strategies in a stable order."""

    PIPELINE = ("resize", "rotate", "flip", "convert", "compress")

    def process(
        self,
        image_path: str | Path,
        options: ProcessingOptions,
    ) -> Image.Image:
        """Process a source file and return a detached Pillow image."""
        with Image.open(image_path) as source_image:
            source_image.load()
            result = source_image.copy()

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
