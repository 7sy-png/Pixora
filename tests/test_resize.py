"""Tests for the resize processing strategy."""

import pytest
from PIL import Image

from app.models import ProcessingOptions
from app.processors import ResizeProcessor


def test_resize_changes_dimensions_without_mutating_source() -> None:
    source = Image.new("RGB", (800, 600), "navy")
    options = ProcessingOptions(width=400, height=300)

    result = ResizeProcessor().process(source, options)

    assert result.size == (400, 300)
    assert source.size == (800, 600)
    assert result is not source


@pytest.mark.parametrize(("width", "height"), [(0, 100), (100, 0), (-1, 50)])
def test_resize_rejects_non_positive_dimensions(width: int, height: int) -> None:
    source = Image.new("RGB", (100, 100))
    options = ProcessingOptions(width=width, height=height)

    with pytest.raises(ValueError, match="больше нуля"):
        ResizeProcessor().process(source, options)
