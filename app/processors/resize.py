"""Image resize strategy."""

from PIL import Image

from app.models import ProcessingOptions
from app.processors.base import ImageProcessor


class ResizeProcessor(ImageProcessor):
    """Resize a Pillow image to the dimensions from processing options."""

    def process(
        self,
        image: Image.Image,
        options: ProcessingOptions,
    ) -> Image.Image:
        """Return a high-quality resized copy of the source image."""
        if options.width <= 0 or options.height <= 0:
            raise ValueError("Размеры изображения должны быть больше нуля")

        target_size = (options.width, options.height)
        if image.size == target_size:
            return image.copy()

        return image.resize(target_size, Image.Resampling.LANCZOS)
