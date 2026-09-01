"""Common interface for image processing strategies."""

from abc import ABC, abstractmethod

from PIL import Image

from app.models import ProcessingOptions


class ImageProcessor(ABC):
    """Define the contract implemented by every processing strategy."""

    @abstractmethod
    def process(
        self,
        image: Image.Image,
        options: ProcessingOptions,
    ) -> Image.Image:
        """Apply one operation and return the resulting Pillow image."""
