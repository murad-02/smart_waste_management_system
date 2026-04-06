from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt


class StatCard(QFrame):
    """A dashboard stat card showing a title, value, and optional subtitle."""

    def __init__(self, title: str, value: str, subtitle: str = "", color: str = "#00b894", parent=None):
        super().__init__(parent)
        self.setProperty("class", "stat-card")
        self.setMinimumSize(180, 120)
        self.setMaximumHeight(140)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(4)

        # Title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #8888aa; font-size: 10pt;")
        self.title_label.setAlignment(Qt.AlignLeft)

        # Value
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            f"color: {color}; font-size: 26pt; font-weight: bold;"
        )
        self.value_label.setAlignment(Qt.AlignLeft)

        # Subtitle
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet("color: #8888aa; font-size: 9pt;")
        self.subtitle_label.setAlignment(Qt.AlignLeft)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.subtitle_label)
        layout.addStretch()

    def update_value(self, value: str):
        self.value_label.setText(value)

    def update_subtitle(self, subtitle: str):
        self.subtitle_label.setText(subtitle)
