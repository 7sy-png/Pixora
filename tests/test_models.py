"""Tests for immutable application data models."""

from pathlib import Path

import pytest

from app.models import ImageInfo


def test_image_info_is_immutable() -> None:
    image_info = ImageInfo(Path("source.png"), "source.png", "PNG", 10, 5, 100)

    with pytest.raises(AttributeError):
        image_info.width = 20  # type: ignore[misc]
