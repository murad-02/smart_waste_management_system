from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class StatCard(QFrame):
    """Dashboard stat card with left icon, title, value, and subtitle."""

    def __init__(self, title: str, value: str, subtitle: str = "",
                 color: str = "#7C3AED", icon: str = "", parent=None):
        super().__init__(parent)
        self.color = color
        self.setProperty("class", "stat-card")
        # Tall enough that title + 22pt digits + subtitle all fit without
        # clipping the digit ascent or letting the subtitle ride into the value.
        self.setMinimumSize(220, 160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # Left icon
        if icon:
            self.icon_label = QLabel(icon)
            self.icon_label.setFont(QFont("Segoe UI Emoji", 24))
            self.icon_label.setAlignment(Qt.AlignCenter)
            self.icon_label.setFixedSize(58, 58)
            self.icon_label.setStyleSheet(
                f"background-color: rgba(124, 58, 237, 0.12); "
                f"border-radius: 14px; color: {color};"
            )
            main_layout.addWidget(self.icon_label, 0, Qt.AlignVCenter)

        # Text column
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        text_layout.setContentsMargins(0, 0, 0, 0)

        # Title (bold)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            "color: #475569; font-size: 10pt; font-weight: bold;"
        )
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.title_label.setFixedHeight(20)

        # Value — fixed height so the digit ascent is never clipped.
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            f"color: {color}; font-size: 22pt; font-weight: bold;"
        )
        self.value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.value_label.setFixedHeight(48)

        # Subtitle
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet("color: #94A3B8; font-size: 9pt;")
        self.subtitle_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.subtitle_label.setFixedHeight(18)

        text_layout.addStretch(1)
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.value_label)
        text_layout.addWidget(self.subtitle_label)
        text_layout.addStretch(1)

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
                "color: #EF4444; font-size: 22pt; font-weight: bold;"
            )
            if hasattr(self, "icon_label"):
                self.icon_label.setStyleSheet(
                    "background-color: rgba(239, 68, 68, 0.12); "
                    "border-radius: 12px; color: #EF4444;"
                )
        else:
            self.setProperty("class", "stat-card")
            self.value_label.setStyleSheet(
                f"color: {self.color}; font-size: 22pt; font-weight: bold;"
            )
            if hasattr(self, "icon_label"):
                self.icon_label.setStyleSheet(
                    f"background-color: rgba(124, 58, 237, 0.12); "
                    f"border-radius: 12px; color: {self.color};"
                )
        self.style().unpolish(self)
        self.style().polish(self)
