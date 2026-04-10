from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class StatCard(QFrame):
    """Dashboard stat card with left icon, title, value, and subtitle."""

    def __init__(self, title: str, value: str, subtitle: str = "",
                 color: str = "#52796A", icon: str = "", parent=None):
        super().__init__(parent)
        self.color = color
        self.setProperty("class", "stat-card")
        self.setMinimumSize(180, 130)
        self.setMaximumHeight(150)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Left icon
        if icon:
            self.icon_label = QLabel(icon)
            self.icon_label.setFont(QFont("Segoe UI Emoji", 26))
            self.icon_label.setAlignment(Qt.AlignCenter)
            self.icon_label.setFixedSize(56, 56)
            self.icon_label.setStyleSheet(
                f"background-color: rgba(82, 121, 106, 0.15); "
                f"border-radius: 12px; color: {color};"
            )
            main_layout.addWidget(self.icon_label, 0, Qt.AlignVCenter)

        # Text column
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        # Title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #BFC5C9; font-size: 10pt;")
        self.title_label.setAlignment(Qt.AlignLeft)

        # Value
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            f"color: {color}; font-size: 28pt; font-weight: bold;"
        )
        self.value_label.setAlignment(Qt.AlignLeft)

        # Subtitle
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet("color: #8A9095; font-size: 9pt;")
        self.subtitle_label.setAlignment(Qt.AlignLeft)

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.value_label)
        text_layout.addWidget(self.subtitle_label)
        text_layout.addStretch()

        main_layout.addLayout(text_layout, 1)

    def update_value(self, value: str):
        self.value_label.setText(value)

    def update_subtitle(self, subtitle: str):
        self.subtitle_label.setText(subtitle)

    def set_alert_mode(self, active: bool):
        """Highlight the card in red when there are active alerts."""
        if active:
            self.setProperty("class", "stat-card-alert")
            self.value_label.setStyleSheet(
                "color: #E57373; font-size: 28pt; font-weight: bold;"
            )
            if hasattr(self, "icon_label"):
                self.icon_label.setStyleSheet(
                    "background-color: rgba(229, 115, 115, 0.15); "
                    "border-radius: 12px; color: #E57373;"
                )
        else:
            self.setProperty("class", "stat-card")
            self.value_label.setStyleSheet(
                f"color: {self.color}; font-size: 28pt; font-weight: bold;"
            )
            if hasattr(self, "icon_label"):
                self.icon_label.setStyleSheet(
                    f"background-color: rgba(82, 121, 106, 0.15); "
                    f"border-radius: 12px; color: {self.color};"
                )
        self.style().unpolish(self)
        self.style().polish(self)
