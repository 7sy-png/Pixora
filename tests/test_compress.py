"""Tests for image compression and serialization."""

import pytest
from PIL import Image

from app.models import ProcessingOptions
from app.processors import CompressProcessor, ProcessorFactory


@pytest.mark.parametrize("output_format", ["JPEG", "WEBP"])
def test_lower_quality_produces_smaller_encoded_image(output_format: str) -> None:
    source = Image.effect_noise((256, 256), 100).convert("RGB")
    processor = CompressProcessor()

    low_quality = processor.encode(
        source,
        ProcessingOptions(256, 256, output_format=output_format, quality=20),
    )
    high_quality = processor.encode(
        source,
        ProcessingOptions(256, 256, output_format=output_format, quality=95),
    )

    assert len(low_quality) < len(high_quality)


@pytest.mark.parametrize("quality", [0, 101])
def test_compress_rejects_quality_outside_ui_range(quality: int) -> None:
    source = Image.new("RGB", (10, 10))
    options = ProcessingOptions(10, 10, quality=quality)

    with pytest.raises(ValueError, match="от 1 до 100"):
        CompressProcessor().process(source, options)


def test_factory_creates_compress_processor() -> None:
    assert isinstance(ProcessorFactory.create("compress"), CompressProcessor)
