"""Tests for the image reflection strategy."""

from PIL import Image

from app.models import ProcessingOptions
from app.processors import FlipProcessor, ProcessorFactory


def test_flip_horizontal_reverses_pixel_columns() -> None:
    source = Image.new("RGB", (2, 1))
    source.putdata([(255, 0, 0), (0, 0, 255)])
    options = ProcessingOptions(2, 1, flip_horizontal=True)

    result = FlipProcessor().process(source, options)

    assert result.getpixel((0, 0)) == (0, 0, 255)
    assert result.getpixel((1, 0)) == (255, 0, 0)


def test_flip_vertical_reverses_pixel_rows() -> None:
    source = Image.new("RGB", (1, 2))
    source.putdata([(255, 255, 255), (0, 0, 0)])
    options = ProcessingOptions(1, 2, flip_vertical=True)

    result = FlipProcessor().process(source, options)

    assert result.getpixel((0, 0)) == (0, 0, 0)
    assert result.getpixel((0, 1)) == (255, 255, 255)


def test_flip_without_options_returns_independent_copy() -> None:
    source = Image.new("RGB", (2, 2), "green")

    result = FlipProcessor().process(source, ProcessingOptions(2, 2))

    assert result is not source
    assert result.tobytes() == source.tobytes()


def test_factory_creates_flip_processor() -> None:
    assert isinstance(ProcessorFactory.create("flip"), FlipProcessor)
