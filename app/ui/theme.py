"""Application theme helpers."""

from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


DARK_STYLESHEET_PATH = (
    Path(__file__).resolve().parent.parent / "resources" / "styles" / "dark.qss"
)
CHECK_ICON_PATH = (
    Path(__file__).resolve().parent.parent / "resources" / "icons" / "check.svg"
)
LOGO_PATH = (
    Path(__file__).resolve().parent.parent / "resources" / "icons" / "pixora-logo.png"
)
APP_ICON_PATH = (
    Path(__file__).resolve().parent.parent / "resources" / "icons" / "pixora-icon.ico"
)


def load_dark_stylesheet() -> str:
    """Load the dark Qt stylesheet from application resources."""
    stylesheet = DARK_STYLESHEET_PATH.read_text(encoding="utf-8")
    return stylesheet.replace(
        "__CHECK_ICON_PATH__",
        f'"{CHECK_ICON_PATH.as_posix()}"',
    )


def apply_dark_theme(application: QApplication) -> None:
    """Apply Pixora's palette, controls style, and default font."""
    application.setStyle("Fusion")

    font = QFont("Segoe UI")
    font.setPointSize(10)
    application.setFont(font)
    application.setStyleSheet(load_dark_stylesheet())
