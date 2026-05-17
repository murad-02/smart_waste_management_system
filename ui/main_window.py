import os

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QMessageBox
)
from PyQt5.QtCore import Qt

from config import STYLES_DIR
from ui.widgets.sidebar import Sidebar
from ui.login_screen import LoginScreen
from ui.dashboard_screen import DashboardScreen
from ui.detection_screen import DetectionScreen
from ui.history_screen import HistoryScreen
from ui.users_screen import UsersScreen
from ui.alerts_screen import AlertsScreen
from ui.reports_screen import ReportsScreen
from ui.settings_screen import SettingsScreen
from ui.fleet.fleet_dashboard import FleetDashboardScreen
from ui.fleet.trucks_screen import TrucksScreen
from ui.fleet.drivers_screen import DriversScreen
from ui.fleet.routes_screen import RoutesScreen
from ui.fleet.trips_screen import TripsScreen
from ui.fleet.maintenance_screen import MaintenanceScreen
from core.log_manager import LogManager


class MainWindow(QMainWindow):
    """Main application window with login and content areas."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Waste Management System")
        self.setMinimumSize(1200, 750)
        self.current_user = None
        self.log = LogManager()

        self._load_stylesheet()
        self._build_ui()
        self._show_login()

    def _load_stylesheet(self):
        qss_path = os.path.join(STYLES_DIR, "main.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _build_ui(self):
        # Central widget that holds the login screen and the main content
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)

        # --- Login Screen ---
        self.login_screen = LoginScreen()
        self.login_screen.login_success.connect(self._on_login_success)
        self.central_widget.addWidget(self.login_screen)

        # --- Main App Layout (sidebar + content) ---
        self.app_widget = QWidget()
        app_layout = QHBoxLayout(self.app_widget)
        app_layout.setContentsMargins(0, 0, 0, 0)
        app_layout.setSpacing(0)

        # Sidebar (placeholder — will be rebuilt on login based on role)
        self.sidebar = None

        # Content stack
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("content-area")

        # Screens
        self.dashboard_screen = DashboardScreen()
        self.detection_screen = DetectionScreen()
        self.history_screen = HistoryScreen()
        self.users_screen = UsersScreen()
        self.alerts_screen = AlertsScreen()
        self.reports_screen = ReportsScreen()
        self.settings_screen = SettingsScreen()

        # Fleet module screens
        self.fleet_dashboard_screen = FleetDashboardScreen()
        self.trucks_screen = TrucksScreen()
        self.drivers_screen = DriversScreen()
        self.routes_screen = RoutesScreen()
        self.trips_screen = TripsScreen()
        self.maintenance_screen = MaintenanceScreen()

        self.screens = {
            "dashboard": self.dashboard_screen,
            "detection": self.detection_screen,
            "history": self.history_screen,
            "fleet_dashboard": self.fleet_dashboard_screen,
            "trucks": self.trucks_screen,
            "drivers": self.drivers_screen,
            "routes": self.routes_screen,
            "trips": self.trips_screen,
            "maintenance": self.maintenance_screen,
            "users": self.users_screen,
            "alerts": self.alerts_screen,
            "reports": self.reports_screen,
            "settings": self.settings_screen,
        }

        for screen in self.screens.values():
            self.content_stack.addWidget(screen)

        app_layout.addWidget(self.content_stack)
        self.central_widget.addWidget(self.app_widget)

    def _show_login(self):
        self.login_screen.reset()
        self.central_widget.setCurrentWidget(self.login_screen)

    def _on_login_success(self, user):
        self.current_user = user

        # Update all screens with current user
        for screen in self.screens.values():
            if hasattr(screen, "set_user"):
                screen.set_user(user)

        # Rebuild sidebar based on user role
        self._setup_sidebar(user.role)

        # Switch to app view
        self.central_widget.setCurrentWidget(self.app_widget)

        # Show dashboard
        self._navigate_to("dashboard")

    def _setup_sidebar(self, role: str):
        # Remove old sidebar if exists
        if self.sidebar:
            self.sidebar.setParent(None)
            self.sidebar.deleteLater()

        self.sidebar = Sidebar(user_role=role)
        self.sidebar.page_changed.connect(self._navigate_to)
        self.sidebar.logout_btn.clicked.connect(self._on_logout)

        if self.current_user:
            self.sidebar.set_user_info(self.current_user.full_name, self.current_user.role)

        # Insert sidebar at position 0 in the app layout
        app_layout = self.app_widget.layout()
        app_layout.insertWidget(0, self.sidebar)

    def _navigate_to(self, page_key: str):
        screen = self.screens.get(page_key)
        if screen:
            self.content_stack.setCurrentWidget(screen)
            # Refresh data when navigating to a screen
            if hasattr(screen, "refresh_data"):
                screen.refresh_data()

    def _on_logout(self):
        reply = QMessageBox.question(
            self, "Logout", "Are you sure you want to logout?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.current_user:
                self.log.log_activity(
                    self.current_user.id, "logout",
                    f"User '{self.current_user.username}' logged out"
                )
            self.current_user = None
            self._show_login()
