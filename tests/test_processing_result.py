"""Tests for completed processing metadata."""

from pathlib import Path

import pytest

from app.models import ImageInfo, ProcessingResult


def test_processing_result_calculates_signed_savings() -> None:
    source = ImageInfo(Path("source.png"), "source.png", "PNG", 100, 50, 1000)

    smaller = ProcessingResult(source, "WEBP", 50, 25, 250, 80)
    larger = ProcessingResult(source, "PNG", 200, 100, 1250, 80)

    assert smaller.saved_percentage == pytest.approx(75.0)
    assert larger.saved_percentage == pytest.approx(-25.0)
