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


@pytest.mark.parametrize(
    ("angle", "expected_pixels"),
    [
        (90, [(5, 0, 0), (3, 0, 0), (1, 0, 0)]),
        (-90, [(2, 0, 0), (4, 0, 0), (6, 0, 0)]),
    ],
)
def test_positive_rotation_is_clockwise(
    angle: int,
    expected_pixels: list[tuple[int, int, int]],
) -> None:
    source = Image.new("RGB", (2, 3))
    source.putdata([(value, 0, 0) for value in range(1, 7)])

    result = RotateProcessor().process(
        source,
        ProcessingOptions(2, 3, rotation=angle),
    )

    assert [result.getpixel((x, 0)) for x in range(3)] == expected_pixels


def test_factory_creates_rotate_processor() -> None:
    assert isinstance(ProcessorFactory.create("rotate"), RotateProcessor)
