"""SQLite repository for processing history."""

from datetime import datetime
from pathlib import Path
import sqlite3

from app.database import Database
from app.models import HistoryRecord


class HistoryRepository:
    """Persist and retrieve processing history records."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def add(self, record: HistoryRecord) -> HistoryRecord:
        """Insert a record and return its persisted representation."""
        with self.database.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO processing_history (
                    original_filename,
                    original_path,
                    output_path,
                    original_format,
                    output_format,
                    original_width,
                    original_height,
                    output_width,
                    output_height,
                    original_size,
                    output_size,
                    quality
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.original_filename,
                    str(record.original_path),
                    str(record.output_path),
                    record.original_format,
                    record.output_format,
                    record.original_width,
                    record.original_height,
                    record.output_width,
                    record.output_height,
                    record.original_size,
                    record.output_size,
                    record.quality,
                ),
            )
            record_id = cursor.lastrowid

        persisted_record = self.get_by_id(record_id)
        if persisted_record is None:
            raise RuntimeError("Не удалось прочитать сохранённую запись истории")
        return persisted_record

    def get_by_id(self, record_id: int) -> HistoryRecord | None:
        """Return one record by primary key."""
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM processing_history WHERE id = ?",
                (record_id,),
            ).fetchone()
        return self._record_from_row(row) if row is not None else None

    def list_all(self) -> list[HistoryRecord]:
        """Return the newest processing operations first."""
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM processing_history
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
        return [self._record_from_row(row) for row in rows]

    def delete_all(self) -> int:
        """Delete all history records and return the affected row count."""
        with self.database.connection() as connection:
            cursor = connection.execute("DELETE FROM processing_history")
            return cursor.rowcount

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> HistoryRecord:
        """Convert a SQLite row to the domain model."""
        return HistoryRecord(
            id=row["id"],
            original_filename=row["original_filename"],
            original_path=Path(row["original_path"]),
            output_path=Path(row["output_path"]),
            original_format=row["original_format"],
            output_format=row["output_format"],
            original_width=row["original_width"],
            original_height=row["original_height"],
            output_width=row["output_width"],
            output_height=row["output_height"],
            original_size=row["original_size"],
            output_size=row["output_size"],
            quality=row["quality"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
