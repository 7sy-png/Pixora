"""Factory for image processing strategies."""

from collections.abc import Callable

from app.processors.base import ImageProcessor
from app.processors.resize import ResizeProcessor


class ProcessorFactory:
    """Create processing strategies by their stable operation name."""

    _creators: dict[str, Callable[[], ImageProcessor]] = {
        "resize": ResizeProcessor,
    }

    @classmethod
    def create(cls, operation: str) -> ImageProcessor:
        """Create a processor or raise a clear error for an unknown operation."""
        normalized_operation = operation.strip().lower()
        try:
            creator = cls._creators[normalized_operation]
        except KeyError as error:
            raise ValueError(f"Неизвестная операция обработки: {operation}") from error

        return creator()
