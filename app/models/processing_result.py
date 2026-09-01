"""Completed image processing result model."""

from dataclasses import dataclass

from app.models.image_info import ImageInfo


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    """Describe source and encoded output metadata for the result UI."""

    source: ImageInfo
    output_format: str
    output_width: int
    output_height: int
    output_size: int
    quality: int

    @property
    def saved_percentage(self) -> float:
        """Return signed storage savings relative to the source file."""
        if self.source.size == 0:
            return 0.0
        return (1 - self.output_size / self.source.size) * 100
