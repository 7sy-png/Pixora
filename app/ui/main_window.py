"""Main application window."""

from PySide6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    """Top-level window of the Pixora application."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pixora")
        self.setMinimumSize(960, 640)
