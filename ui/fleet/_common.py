"""Shared UI helpers for fleet screens."""

from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox,
    QTableWidgetItem
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt


HEADER_STYLE = "font-size: 20pt; font-weight: bold; color: #E5E5E5;"
SUBTLE_STYLE = "color: #BFC5C9; font-size: 11pt;"


def build_header(title: str, subtitle: str = ""):
    """Build the standard fleet-screen header (returns a QHBoxLayout)."""
    row = QHBoxLayout()
    row.setSpacing(12)

    col = QHBoxLayout()
    label = QLabel(title)
    label.setStyleSheet(HEADER_STYLE)
    col.addWidget(label)
    if subtitle:
        sub = QLabel(f" — {subtitle}")
        sub.setStyleSheet(SUBTLE_STYLE)
        col.addWidget(sub)
    row.addLayout(col)
    row.addStretch()
    return row


def primary_button(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setProperty("class", "accent")
    btn.setCursor(Qt.PointingHandCursor)
    return btn


def secondary_button(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFixedHeight(30)
    btn.setStyleSheet(
        "background-color: #2A2F33; color: #E5E5E5; border: 1px solid #3A3F44; "
        "border-radius: 4px; padding: 2px 12px; font-size: 10pt; min-height: 0px;"
    )
    return btn


def danger_button(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFixedHeight(30)
    btn.setStyleSheet(
        "background-color: #E57373; color: #1A1D1F; border: none; border-radius: 4px; "
        "font-weight: bold; padding: 2px 12px; font-size: 10pt; min-height: 0px;"
    )
    return btn


def filter_bar(parent_layout, *, search_placeholder: str = "Search…",
               status_options=None):
    """Build a [search line edit] [status combo] [Apply] row.

    Returns (search_input, status_combo, apply_btn).
    """
    bar = QFrame()
    bar.setStyleSheet(
        "QFrame { background-color: #222629; border: 1px solid #2E3338;"
        " border-radius: 8px; padding: 4px; }"
    )
    layout = QHBoxLayout(bar)
    layout.setContentsMargins(12, 8, 12, 8)
    layout.setSpacing(10)

    search = QLineEdit()
    search.setPlaceholderText(search_placeholder)
    search.setStyleSheet(
        "QLineEdit { background-color: #1A1D1F; color: #E5E5E5; "
        "border: 1px solid #3A3F44; border-radius: 4px; padding: 6px 10px; }"
    )
    layout.addWidget(search, 3)

    status_combo = None
    if status_options:
        status_combo = QComboBox()
        status_combo.addItem("All statuses", "")
        for value in status_options:
            status_combo.addItem(value.replace("_", " ").title(), value)
        layout.addWidget(status_combo, 1)

    apply_btn = primary_button("Apply")
    apply_btn.setFixedHeight(32)
    layout.addWidget(apply_btn)

    parent_layout.addWidget(bar)
    return search, status_combo, apply_btn


def colored_status_item(text: str, color_hex: str,
                        text_color: str = "#1A1D1F") -> QTableWidgetItem:
    item = QTableWidgetItem(text.replace("_", " ").title())
    item.setBackground(QColor(color_hex))
    item.setForeground(QColor(text_color))
    item.setTextAlignment(Qt.AlignCenter)
    return item


# Status → colour mapping shared across truck/driver/trip tables
STATUS_COLORS = {
    # Trucks
    "available":       ("#4CAF50", "#E5E5E5"),
    "on_route":        ("#64B5F6", "#1A1D1F"),
    "maintenance":     ("#FFC107", "#1A1D1F"),
    "out_of_service":  ("#E57373", "#1A1D1F"),
    "inactive":        ("#8A9095", "#1A1D1F"),
    # Drivers
    "on_duty":         ("#52796A", "#E5E5E5"),
    "off_duty":        ("#BFC5C9", "#1A1D1F"),
    "suspended":       ("#E57373", "#1A1D1F"),
    # Routes
    "active":          ("#4CAF50", "#E5E5E5"),
    "draft":           ("#FFC107", "#1A1D1F"),
    # Trips
    "scheduled":       ("#64B5F6", "#1A1D1F"),
    "completed":       ("#4CAF50", "#E5E5E5"),
    "cancelled":       ("#8A9095", "#1A1D1F"),
}


def status_item(status: str) -> QTableWidgetItem:
    bg, fg = STATUS_COLORS.get(status, ("#BFC5C9", "#1A1D1F"))
    return colored_status_item(status, bg, fg)
