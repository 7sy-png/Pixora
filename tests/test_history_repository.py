"""Tests for the SQLite history repository."""

from pathlib import Path

from app.database import Database
from app.models import HistoryRecord
from app.repositories import HistoryRepository


def make_record(filename: str = "source.png") -> HistoryRecord:
    """Create a representative unpersisted history record."""
    return HistoryRecord(
        original_filename=filename,
        original_path=Path(f"C:/images/{filename}"),
        output_path=Path(f"C:/output/{Path(filename).stem}.webp"),
        original_format="PNG",
        output_format="WEBP",
        original_width=1920,
        original_height=1080,
        output_width=1280,
        output_height=720,
        original_size=1_000_000,
        output_size=250_000,
        quality=80,
    )


def test_repository_adds_and_reads_history_record(tmp_path) -> None:
    repository = HistoryRepository(Database(tmp_path / "history.db"))

    persisted = repository.add(make_record())

    assert persisted.id is not None
    assert persisted.created_at is not None
    assert persisted.saved_percentage == 75.0
    assert repository.get_by_id(persisted.id) == persisted


def test_repository_lists_newest_records_first(tmp_path) -> None:
    database = Database(tmp_path / "history.db")
    repository = HistoryRepository(database)
    first = repository.add(make_record("first.png"))
    second = repository.add(make_record("second.png"))

    records = HistoryRepository(database).list_all()

    assert [record.id for record in records] == [second.id, first.id]
