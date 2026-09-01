"""Non-blocking toast notification widget."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class ToastNotification(QFrame):
    """Show a short success, error, or informational message."""

    ICONS = {
        "success": "✓",
        "error": "✕",
        "info": "i",
    }

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("toastNotification")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setMaximumWidth(360)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 11, 16, 11)
        layout.setSpacing(10)

        self._icon_label = QLabel(self)
        self._icon_label.setObjectName("toastIcon")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon_label)

        self._message_label = QLabel(self)
        self._message_label.setObjectName("toastMessage")
        self._message_label.setWordWrap(True)
        layout.addWidget(self._message_label, stretch=1)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        self.hide()

    def show_message(
        self,
        message: str,
        kind: str = "info",
        duration_ms: int = 3000,
    ) -> None:
        """Display a styled message and restart its auto-hide timer."""
        if kind not in self.ICONS:
            raise ValueError(f"Неизвестный тип уведомления: {kind}")

        self.setProperty("kind", kind)
        self._icon_label.setText(self.ICONS[kind])
        self._message_label.setText(message)
        self.style().unpolish(self)
        self.style().polish(self)
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()
        self._hide_timer.start(duration_ms)

    def reposition(self) -> None:
        """Keep the toast above the parent's lower-right corner."""
        parent = self.parentWidget()
        if parent is None:
            return

        margin = 20
        x = max(margin, parent.width() - self.width() - margin)
        y = max(margin, parent.height() - self.height() - margin)
        self.move(x, y)
