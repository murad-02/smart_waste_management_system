"""Shared UI helpers for fleet screens."""

from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox,
    QTableWidgetItem
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt


HEADER_STYLE = "font-size: 20pt; font-weight: bold; color: #0F172A;"
SUBTLE_STYLE = "color: #64748B; font-size: 11pt;"


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
        "background-color: #F1F5F9; color: #0F172A; border: 1px solid #D1D5DB; "
        "border-radius: 4px; padding: 2px 12px; font-size: 10pt; min-height: 0px;"
    )
    return btn


def danger_button(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFixedHeight(30)
    btn.setStyleSheet(
        "background-color: #EF4444; color: #FFFFFF; border: none; border-radius: 4px; "
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
        "QFrame { background-color: #FFFFFF; border: 1px solid #E5E7EB;"
        " border-radius: 8px; padding: 4px; }"
    )
    layout = QHBoxLayout(bar)
    layout.setContentsMargins(12, 8, 12, 8)
    layout.setSpacing(10)

    search = QLineEdit()
    search.setPlaceholderText(search_placeholder)
    search.setStyleSheet(
        "QLineEdit { background-color: #F8FAFC; color: #0F172A; "
        "border: 1px solid #D1D5DB; border-radius: 4px; padding: 6px 10px; }"
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
                        text_color: str = "#0F172A") -> QTableWidgetItem:
    item = QTableWidgetItem(text.replace("_", " ").title())
    item.setBackground(QColor(color_hex))
    item.setForeground(QColor(text_color))
    item.setTextAlignment(Qt.AlignCenter)
    return item


# Status → colour mapping shared across truck/driver/trip tables.
# Soft pill palette: (background, text)
STATUS_COLORS = {
    # Trucks
    "available":       ("#D1FAE5", "#047857"),
    "on_route":        ("#DBEAFE", "#1D4ED8"),
    "maintenance":     ("#FEF3C7", "#B45309"),
    "out_of_service":  ("#FEE2E2", "#B91C1C"),
    "inactive":        ("#F1F5F9", "#475569"),
    # Drivers
    "on_duty":         ("#EDE9FE", "#6D28D9"),
    "off_duty":        ("#F1F5F9", "#475569"),
    "suspended":       ("#FEE2E2", "#B91C1C"),
    # Routes
    "active":          ("#D1FAE5", "#047857"),
    "draft":           ("#FEF3C7", "#B45309"),
    # Trips
    "scheduled":       ("#DBEAFE", "#1D4ED8"),
    "completed":       ("#D1FAE5", "#047857"),
    "cancelled":       ("#F1F5F9", "#475569"),
}


def status_item(status: str) -> QTableWidgetItem:
    bg, fg = STATUS_COLORS.get(status, ("#F1F5F9", "#475569"))
    return colored_status_item(status, bg, fg)
