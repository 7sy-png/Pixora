"""Image processing strategies."""

from app.processors.base import ImageProcessor
from app.processors.compress import CompressProcessor
from app.processors.convert import ConvertProcessor
from app.processors.factory import ProcessorFactory
from app.processors.resize import ResizeProcessor

__all__ = [
    "CompressProcessor",
    "ConvertProcessor",
    "ImageProcessor",
    "ProcessorFactory",
    "ResizeProcessor",
]
