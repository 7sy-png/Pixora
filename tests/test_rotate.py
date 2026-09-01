"""Tests for the image rotation strategy."""

import pytest
from PIL import Image

from app.models import ProcessingOptions
from app.processors import ProcessorFactory, RotateProcessor


@pytest.mark.parametrize(
    ("angle", "expected_size"),
    [(-90, (3, 2)), (90, (3, 2)), (180, (2, 3)), (0, (2, 3))],
)
def test_rotate_uses_lossless_right_angle_operations(
    angle: int,
    expected_size: tuple[int, int],
) -> None:
    source = Image.new("RGB", (2, 3), "red")
    options = ProcessingOptions(2, 3, rotation=angle)

    result = RotateProcessor().process(source, options)

    assert result.size == expected_size
    assert source.size == (2, 3)
    assert result is not source


def test_rotate_rejects_unsupported_angle() -> None:
    with pytest.raises(ValueError, match="-90, 90 и 180"):
        RotateProcessor().process(
            Image.new("RGB", (10, 10)),
            ProcessingOptions(10, 10, rotation=45),
        )


def test_factory_creates_rotate_processor() -> None:
    assert isinstance(ProcessorFactory.create("rotate"), RotateProcessor)
