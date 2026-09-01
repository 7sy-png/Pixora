"""Image reflection strategy."""

from PIL import Image

from app.models import ProcessingOptions
from app.processors.base import ImageProcessor


class FlipProcessor(ImageProcessor):
    """Reflect an image horizontally, vertically, or in both directions."""

    def process(
        self,
        image: Image.Image,
        options: ProcessingOptions,
    ) -> Image.Image:
        """Return a reflected copy without mutating the source image."""
        result = image.copy()
        if options.flip_horizontal:
            result = result.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if options.flip_vertical:
            result = result.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        return result
