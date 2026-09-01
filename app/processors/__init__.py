"""Image processing strategies."""

from app.processors.base import ImageProcessor
from app.processors.resize import ResizeProcessor

__all__ = ["ImageProcessor", "ResizeProcessor"]
