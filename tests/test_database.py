"""Tests for SQLite initialization."""

from app.database import Database


def test_database_creates_processing_history_schema(tmp_path) -> None:
    database_path = tmp_path / "nested" / "pixora.db"

    database = Database(database_path)

    assert database_path.is_file()
    with database.connection() as connection:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(processing_history)")
        }

    assert {
        "id",
        "original_filename",
        "original_path",
        "output_path",
        "original_format",
        "output_format",
        "original_width",
        "original_height",
        "output_width",
        "output_height",
        "original_size",
        "output_size",
        "quality",
        "created_at",
    } <= columns
