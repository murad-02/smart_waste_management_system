from PyQt5.QtWidgets import QFrame, QLabel, QHBoxLayout, QGraphicsOpacityEffect
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont


class Toast(QFrame):
    """A temporary popup notification (toast) that auto-dismisses."""

    STYLES = {
        "success": ("toast-success", "\u2714"),
        "error": ("toast-error", "\u2718"),
        "warning": ("toast-warning", "\u26a0"),
        "info": ("toast-info", "\u2139"),
    }

    def __init__(self, message: str, toast_type: str = "info",
                 duration: int = 3000, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        class_name, icon = self.STYLES.get(toast_type, self.STYLES["info"])
        self.setProperty("class", class_name)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI", 14))
        icon_label.setStyleSheet("background: transparent;")

        msg_label = QLabel(message)
        msg_label.setFont(QFont("Segoe UI", 11))
        msg_label.setStyleSheet("background: transparent;")
        msg_label.setWordWrap(True)

        layout.addWidget(icon_label)
        layout.addWidget(msg_label, 1)

        self.setMinimumWidth(300)
        self.setMaximumWidth(500)
        self.adjustSize()

        # Auto dismiss
        QTimer.singleShot(duration, self.close)

    def show_toast(self, parent_widget=None):
        """Position the toast at the top-right of the parent and show it."""
        if parent_widget:
            parent_geo = parent_widget.geometry()
            x = parent_geo.x() + parent_geo.width() - self.width() - 20
            y = parent_geo.y() + 60
            self.move(x, y)
        self.show()


def show_toast(parent, message: str, toast_type: str = "info", duration: int = 3000):
    """Convenience function to show a toast notification."""
    toast = Toast(message, toast_type, duration, parent)
    toast.show_toast(parent.window() if parent else None)
    return toast
