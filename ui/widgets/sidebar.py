from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpacerItem,
    QSizePolicy
)
from PyQt5.QtCore import pyqtSignal, Qt


class Sidebar(QWidget):
    """Navigation sidebar with role-based menu items and icon system."""

    page_changed = pyqtSignal(str)

    # Menu items: (page_key, display_text, icon_char, required_role)
    # A `None` page_key renders a non-clickable section heading.
    MENU_ITEMS = [
        ("dashboard", "Dashboard", "\U0001f4ca", "operator"),               # core
        ("detection", "Detection", "\U0001f4f7", "operator"),
        ("history", "Waste History", "\U0001f4cb", "operator"),
        (None, "Fleet Operations", "", "operator"),                         # heading
        ("fleet_dashboard", "Fleet Dashboard", "\U0001f4c8", "operator"),
        ("trucks", "Trucks", "\U0001f69b", "operator"),
        ("drivers", "Drivers", "\U0001f9d1", "supervisor"),
        ("routes", "Routes", "\U0001f5fa", "operator"),
        ("trips", "Trips", "\U0001f4cd", "operator"),
        ("maintenance", "Maintenance", "\U0001f527", "supervisor"),
        (None, "Administration", "", "operator"),                           # heading
        ("users", "Users", "\U0001f464", "admin"),
        ("alerts", "Alerts", "⚠️", "supervisor"),
        ("reports", "Reports", "\U0001f4c8", "operator"),
        ("settings", "Settings", "⚙️", "admin"),
    ]

    ROLE_HIERARCHY = {"admin": 3, "supervisor": 2, "operator": 1}

    def __init__(self, user_role: str = "operator", parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(230)
        self.user_role = user_role
        self.current_page = "dashboard"
        self.buttons = {}

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # App logo / title
        header = QLabel("  ♻  SWMS")
        header.setStyleSheet(
            "color: #52796A; font-size: 18pt; font-weight: bold; "
            "padding: 24px 16px 4px 16px;"
        )
        layout.addWidget(header)

        # Version
        version_label = QLabel("  v1.1.0 — Fleet Edition")
        version_label.setStyleSheet(
            "color: #8A9095; font-size: 9pt; padding-left: 16px; padding-bottom: 10px;"
        )
        layout.addWidget(version_label)

        # Separator
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #2E3338; margin: 0 14px;")
        layout.addWidget(sep)

        layout.addSpacing(8)

        # Navigation buttons
        user_level = self.ROLE_HIERARCHY.get(self.user_role, 1)

        for page_key, text, icon, required_role in self.MENU_ITEMS:
            required_level = self.ROLE_HIERARCHY.get(required_role, 1)
            if user_level < required_level:
                continue

            # Section heading
            if page_key is None:
                heading = QLabel(text.upper())
                heading.setStyleSheet(
                    "color: #6E767D; font-size: 9pt; font-weight: bold; "
                    "letter-spacing: 1px; padding: 16px 18px 6px 18px;"
                )
                layout.addWidget(heading)
                continue

            label_text = f"  {icon}  {text}" if icon else f"  {text}"
            btn = QPushButton(label_text)
            btn.setProperty("class", "sidebar-btn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, key=page_key: self._on_click(key))
            self.buttons[page_key] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # User info / logout at bottom
        self.user_label = QLabel("")
        self.user_label.setStyleSheet(
            "color: #BFC5C9; font-size: 9pt; padding: 8px 16px;"
        )
        self.user_label.setWordWrap(True)
        layout.addWidget(self.user_label)

        self.logout_btn = QPushButton("  \U0001f6aa  Logout")
        self.logout_btn.setProperty("class", "sidebar-btn")
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.setStyleSheet(
            "color: #E57373; text-align: left; padding: 12px 16px; "
            "margin: 2px 10px 18px 10px;"
        )
        layout.addWidget(self.logout_btn)

        # Set default active
        self._update_active_button("dashboard")

    def _on_click(self, page_key: str):
        if page_key != self.current_page:
            self.current_page = page_key
            self._update_active_button(page_key)
            self.page_changed.emit(page_key)

    def _update_active_button(self, active_key: str):
        for key, btn in self.buttons.items():
            if key == active_key:
                btn.setProperty("class", "sidebar-btn-active")
            else:
                btn.setProperty("class", "sidebar-btn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def set_user_info(self, full_name: str, role: str):
        self.user_label.setText(f"\U0001f464 {full_name}\n    Role: {role.capitalize()}")
