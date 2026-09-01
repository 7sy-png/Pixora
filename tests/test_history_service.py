"""Tests for the processing history service."""

from pathlib import Path

from app.database import Database
from app.models import ImageInfo, ProcessingResult
from app.repositories import HistoryRepository
from app.services import HistoryService


def test_history_service_maps_and_persists_processing_result(tmp_path) -> None:
    repository = HistoryRepository(Database(tmp_path / "history.db"))
    service = HistoryService(repository)
    source = ImageInfo(
        path=Path("C:/images/source.png"),
        filename="source.png",
        format="PNG",
        width=1920,
        height=1080,
        size=1_000_000,
    )
    result = ProcessingResult(
        source=source,
        output_format="WEBP",
        output_width=1280,
        output_height=720,
        output_size=200_000,
        quality=75,
    )

    persisted = service.record_processing(result, "C:/output/result.webp")

    assert persisted.id is not None
    assert persisted.output_path == Path("C:/output/result.webp")
    assert persisted.saved_percentage == 80.0
    assert service.get_history() == [persisted]

    assert service.clear_history() == 1
    assert service.get_history() == []
