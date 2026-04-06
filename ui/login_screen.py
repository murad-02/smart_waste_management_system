from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont

from core.auth_manager import AuthManager
from core.log_manager import LogManager


class LoginScreen(QWidget):
    """Full-screen login form with centered card layout."""

    login_success = pyqtSignal(object)  # emits User object

    def __init__(self, parent=None):
        super().__init__(parent)
        self.auth = AuthManager()
        self.log = LogManager()
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignCenter)

        # Card container
        card = QFrame()
        card.setObjectName("login-card")
        card.setFixedSize(420, 460)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(12)

        # App icon / title
        icon_label = QLabel("\U0001f5d1")
        icon_label.setFont(QFont("Segoe UI Emoji", 36))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background: transparent;")

        title = QLabel("Smart Waste Management")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #00b894;")

        subtitle = QLabel("Sign in to continue")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 10pt; color: #8888aa;")

        layout.addWidget(icon_label)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(16)

        # Username
        username_label = QLabel("Username")
        username_label.setStyleSheet("font-size: 10pt; color: #8888aa;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setMinimumHeight(40)

        # Password
        password_label = QLabel("Password")
        password_label.setStyleSheet("font-size: 10pt; color: #8888aa;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(40)
        self.password_input.returnPressed.connect(self._on_login)

        # Error message
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("color: #d63031; font-size: 10pt;")
        self.error_label.hide()

        # Login button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setProperty("class", "accent")
        self.login_btn.setMinimumHeight(44)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self._on_login)

        layout.addWidget(username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(password_label)
        layout.addWidget(self.password_input)
        layout.addSpacing(4)
        layout.addWidget(self.error_label)
        layout.addSpacing(8)
        layout.addWidget(self.login_btn)
        layout.addStretch()

        outer.addWidget(card)

    def _on_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            self._show_error("Please enter both username and password.")
            return

        user = self.auth.login(username, password)
        if user:
            self.error_label.hide()
            self.log.log_activity(user.id, "login", f"User '{user.username}' logged in")
            self.login_success.emit(user)
        else:
            self._show_error("Invalid username or password.")

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()

    def reset(self):
        """Clear inputs for next login."""
        self.username_input.clear()
        self.password_input.clear()
        self.error_label.hide()
        self.username_input.setFocus()
