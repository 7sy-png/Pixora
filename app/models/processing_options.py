"""Image processing options model."""

from dataclasses import dataclass


@dataclass(slots=True)
class ProcessingOptions:
    """Collect all settings used by the image-processing pipeline."""

    width: int
    height: int
    keep_aspect_ratio: bool = True
    output_format: str = "JPEG"
    quality: int = 80
    rotation: int = 0
    flip_horizontal: bool = False
    flip_vertical: bool = False
