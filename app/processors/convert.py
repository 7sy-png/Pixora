"""Image format conversion strategy."""

from PIL import Image

from app.models import ProcessingOptions
from app.processors.base import ImageProcessor


class ConvertProcessor(ImageProcessor):
    """Prepare a Pillow image for saving in the requested output format."""

    SUPPORTED_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})

    def process(
        self,
        image: Image.Image,
        options: ProcessingOptions,
    ) -> Image.Image:
        """Return an image with a mode supported by the output format."""
        output_format = options.output_format.strip().upper()
        if output_format == "JPG":
            output_format = "JPEG"
        if output_format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Неподдерживаемый формат: {options.output_format}")

        if output_format == "JPEG":
            return self._prepare_jpeg(image)
        if output_format == "WEBP":
            return self._prepare_webp(image)
        return self._prepare_png(image)

    def _prepare_jpeg(self, image: Image.Image) -> Image.Image:
        """Remove transparency over white because JPEG has no alpha channel."""
        if not self._has_transparency(image):
            return image.convert("RGB")

        rgba_image = image.convert("RGBA")
        background = Image.new("RGB", rgba_image.size, "white")
        background.paste(rgba_image, mask=rgba_image.getchannel("A"))
        return background

    def _prepare_png(self, image: Image.Image) -> Image.Image:
        """Preserve PNG-compatible color modes and transparency."""
        if image.mode == "CMYK":
            return image.convert("RGB")
        return image.copy()

    def _prepare_webp(self, image: Image.Image) -> Image.Image:
        """Convert the source to RGB or RGBA as required by WebP."""
        if image.mode in {"RGB", "RGBA"}:
            return image.copy()
        return image.convert("RGBA" if self._has_transparency(image) else "RGB")

    @staticmethod
    def _has_transparency(image: Image.Image) -> bool:
        """Detect explicit alpha channels and palette transparency."""
        return image.mode in {"RGBA", "LA"} or (
            image.mode == "P" and "transparency" in image.info
        )
