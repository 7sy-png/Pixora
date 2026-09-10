"""Tests for transport models used by the distributed services."""

import pytest
from pydantic import ValidationError

from app.distributed.contracts import ProcessingOptionsPayload


def test_processing_payload_normalizes_jpg_and_builds_domain_model() -> None:
    payload = ProcessingOptionsPayload.model_validate(
        {
            "width": 800,
            "height": 600,
            "output_format": " jpg ",
            "quality": 72,
            "rotation": 90,
            "flip_horizontal": True,
        }
    )

    options = payload.to_domain()

    assert payload.output_format == "JPEG"
    assert options.width == 800
    assert options.height == 600
    assert options.output_format == "JPEG"
    assert options.rotation == 90
    assert options.flip_horizontal is True


def test_processing_payload_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ProcessingOptionsPayload.model_validate(
            {
                "width": 100,
                "height": 100,
                "unexpected": "value",
            }
        )


def test_processing_payload_rejects_excessive_pixel_count() -> None:
    with pytest.raises(ValidationError, match="100 миллионов"):
        ProcessingOptionsPayload(
            width=50_000,
            height=50_000,
        )
