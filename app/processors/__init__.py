"""Image processing strategies."""

from app.processors.base import ImageProcessor
from app.processors.compress import CompressProcessor
from app.processors.convert import ConvertProcessor
from app.processors.factory import ProcessorFactory
from app.processors.flip import FlipProcessor
from app.processors.resize import ResizeProcessor
from app.processors.rotate import RotateProcessor

__all__ = [
    "CompressProcessor",
    "ConvertProcessor",
    "FlipProcessor",
    "ImageProcessor",
    "ProcessorFactory",
    "ResizeProcessor",
    "RotateProcessor",
]
