"""Tests for immutable application data models."""

from datetime import datetime
from pathlib import Path

import pytest

from app.models import HistoryRecord, ImageInfo


def test_image_info_is_immutable() -> None:
    image_info = ImageInfo(Path("source.png"), "source.png", "PNG", 10, 5, 100)

    with pytest.raises(AttributeError):
        image_info.width = 20  # type: ignore[misc]


def test_history_record_calculates_signed_savings() -> None:
    record = HistoryRecord(
        original_filename="source.png",
        original_path=Path("source.png"),
        output_path=Path("result.webp"),
        original_format="PNG",
        output_format="WEBP",
        original_width=100,
        original_height=50,
        output_width=50,
        output_height=25,
        original_size=400,
        output_size=100,
        quality=80,
        id=1,
        created_at=datetime(2026, 9, 1, 12, 0),
    )

    assert record.saved_percentage == pytest.approx(75.0)


def test_history_record_handles_empty_source() -> None:
    record = HistoryRecord(
        original_filename="empty.png",
        original_path=Path("empty.png"),
        output_path=Path("result.png"),
        original_format="PNG",
        output_format="PNG",
        original_width=1,
        original_height=1,
        output_width=1,
        output_height=1,
        original_size=0,
        output_size=10,
        quality=80,
    )

    assert record.saved_percentage == 0.0
