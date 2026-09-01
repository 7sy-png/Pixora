"""Tests for the format conversion strategy."""

from io import BytesIO

import pytest
from PIL import Image

from app.models import ProcessingOptions
from app.processors import ConvertProcessor, ProcessorFactory


@pytest.mark.parametrize(
    ("output_format", "expected_mode"),
    [("JPEG", "RGB"), ("PNG", "RGBA"), ("WEBP", "RGBA")],
)
def test_convert_prepares_supported_output_modes(
    output_format: str,
    expected_mode: str,
) -> None:
    source = Image.new("RGBA", (20, 10), (10, 20, 30, 128))
    options = ProcessingOptions(20, 10, output_format=output_format)

    result = ConvertProcessor().process(source, options)

    assert result.mode == expected_mode
    buffer = BytesIO()
    result.save(buffer, format=output_format)
    buffer.seek(0)
    with Image.open(buffer) as reopened:
        assert reopened.format == output_format


def test_convert_rgba_to_jpeg_uses_white_background() -> None:
    source = Image.new("RGBA", (1, 1), (255, 0, 0, 0))
    options = ProcessingOptions(1, 1, output_format="JPEG")

    result = ConvertProcessor().process(source, options)

    assert result.mode == "RGB"
    assert result.getpixel((0, 0)) == (255, 255, 255)


def test_convert_rejects_unknown_format() -> None:
    source = Image.new("RGB", (10, 10))
    options = ProcessingOptions(10, 10, output_format="TIFF")

    with pytest.raises(ValueError, match="Неподдерживаемый формат"):
        ConvertProcessor().process(source, options)


def test_factory_creates_convert_processor() -> None:
    assert isinstance(ProcessorFactory.create("convert"), ConvertProcessor)
