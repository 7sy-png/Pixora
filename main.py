"""Application entry point for Pixora."""

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.services import ImageService
from app.ui.main_window import MainWindow
from app.ui.theme import APP_ICON_PATH, apply_dark_theme


def main() -> int:
    """Create and run the Pixora desktop application."""
    application = QApplication(sys.argv)
    apply_dark_theme(application)
    application.setWindowIcon(QIcon(str(APP_ICON_PATH)))

    window = MainWindow(ImageService())
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
