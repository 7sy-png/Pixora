"""Application entry point for Pixora."""

import sys

from PySide6.QtWidgets import QApplication

from app.database import Database
from app.repositories import HistoryRepository
from app.services import HistoryService, ImageService
from app.ui.main_window import MainWindow
from app.ui.theme import apply_dark_theme


def main() -> int:
    """Create and run the Pixora desktop application."""
    application = QApplication(sys.argv)
    apply_dark_theme(application)

    database = Database()
    history_service = HistoryService(HistoryRepository(database))

    window = MainWindow(ImageService(), history_service)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
