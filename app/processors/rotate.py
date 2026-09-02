"""Image rotation strategy."""

from PIL import Image

from app.models import ProcessingOptions
from app.processors.base import ImageProcessor


class RotateProcessor(ImageProcessor):
    """Rotate images by the right-angle values exposed by the UI."""

    _TRANSPOSE_OPERATIONS = {
        -90: Image.Transpose.ROTATE_90,
        90: Image.Transpose.ROTATE_270,
        180: Image.Transpose.ROTATE_180,
    }

    def process(
        self,
        image: Image.Image,
        options: ProcessingOptions,
    ) -> Image.Image:
        """Rotate clockwise for positive and counter-clockwise for negative."""
        if options.rotation == 0:
            return image.copy()

        try:
            operation = self._TRANSPOSE_OPERATIONS[options.rotation]
        except KeyError as error:
            raise ValueError("Поддерживаются повороты -90, 90 и 180 градусов") from error

        return image.transpose(operation)
