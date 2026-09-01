"""Processing history record model."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class HistoryRecord:
    """Represent one persisted image processing operation."""

    original_filename: str
    original_path: Path
    output_path: Path
    original_format: str
    output_format: str
    original_width: int
    original_height: int
    output_width: int
    output_height: int
    original_size: int
    output_size: int
    quality: int
    id: int | None = None
    created_at: datetime | None = None

    @property
    def saved_percentage(self) -> float:
        """Return signed storage savings relative to the original file."""
        if self.original_size == 0:
            return 0.0
        return (1 - self.output_size / self.original_size) * 100
