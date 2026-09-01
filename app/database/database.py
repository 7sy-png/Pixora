"""SQLite connection and schema initialization."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "pixora.db"


class Database:
    """Own SQLite connections and keep the local schema available."""

    def __init__(self, path: str | Path = DEFAULT_DATABASE_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a configured connection and manage commit or rollback."""
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create the processing history table when it does not exist."""
        with self.connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS processing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_filename TEXT NOT NULL,
                    original_path TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    original_format TEXT NOT NULL,
                    output_format TEXT NOT NULL,
                    original_width INTEGER NOT NULL,
                    original_height INTEGER NOT NULL,
                    output_width INTEGER NOT NULL,
                    output_height INTEGER NOT NULL,
                    original_size INTEGER NOT NULL,
                    output_size INTEGER NOT NULL,
                    quality INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
