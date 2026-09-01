"""Business service for processing history."""

from pathlib import Path

from app.models import HistoryRecord, ProcessingResult
from app.repositories import HistoryRepository


class HistoryService:
    """Translate completed processing results into history records."""

    def __init__(self, repository: HistoryRepository) -> None:
        self.repository = repository

    def record_processing(
        self,
        result: ProcessingResult,
        output_path: str | Path,
    ) -> HistoryRecord:
        """Persist one successfully saved processing result."""
        record = HistoryRecord(
            original_filename=result.source.filename,
            original_path=result.source.path,
            output_path=Path(output_path),
            original_format=result.source.format,
            output_format=result.output_format,
            original_width=result.source.width,
            original_height=result.source.height,
            output_width=result.output_width,
            output_height=result.output_height,
            original_size=result.source.size,
            output_size=result.output_size,
            quality=result.quality,
        )
        return self.repository.add(record)

    def get_history(self) -> list[HistoryRecord]:
        """Return all history records from newest to oldest."""
        return self.repository.list_all()

    def clear_history(self) -> int:
        """Remove all processing history records."""
        return self.repository.delete_all()
