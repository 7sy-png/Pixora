"""Source image metadata model."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ImageInfo:
    """Describe a source image selected by the user."""

    path: Path
    filename: str
    format: str
    width: int
    height: int
    size: int
