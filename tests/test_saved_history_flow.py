"""Integration test for saving output metadata to history."""

from pathlib import Path

from app.database import Database
from app.models import ImageInfo, ProcessingResult
from app.repositories import HistoryRepository
from app.services import HistoryService, ImageService


def test_saved_result_is_recorded_in_history(tmp_path) -> None:
    image_service = ImageService()
    history_service = HistoryService(
        HistoryRepository(Database(tmp_path / "pixora.db"))
    )
    result = ProcessingResult(
        source=ImageInfo(
            path=tmp_path / "source.png",
            filename="source.png",
            format="PNG",
            width=100,
            height=80,
            size=1000,
        ),
        output_format="WEBP",
        output_width=50,
        output_height=40,
        output_size=200,
        quality=80,
    )
    destination = tmp_path / "result.webp"

    saved_path = image_service.save_encoded(b"encoded", destination)
    history_service.record_processing(result, saved_path)

    records = history_service.get_history()
    assert len(records) == 1
    assert records[0].output_path == destination
    assert records[0].output_format == "WEBP"
