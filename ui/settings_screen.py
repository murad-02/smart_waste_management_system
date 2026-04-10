from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QFormLayout, QLineEdit, QGroupBox, QScrollArea, QCheckBox, QMessageBox
)
from PyQt5.QtCore import Qt

from database.db_setup import Session
from database.models import AppSetting
from core.auth_manager import AuthManager
from core.log_manager import LogManager
from core.notification_service import NotificationService
from ui.widgets.toast import show_toast


class SettingsScreen(QWidget):
    """Admin settings screen for SMTP, app, and password management."""

    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.auth = AuthManager()
        self.log = LogManager()
        self.notification = NotificationService()
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        header = QLabel("Settings")
        header.setStyleSheet("font-size: 20pt; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(header)

        # SMTP Settings Group — card style
        smtp_group = QGroupBox("  \u2709  Email / SMTP Configuration")
        smtp_layout = QFormLayout()
        smtp_layout.setSpacing(12)

        self.smtp_server = QLineEdit()
        self.smtp_server.setPlaceholderText("e.g., smtp.gmail.com")
        smtp_layout.addRow("SMTP Server:", self.smtp_server)

        self.smtp_port = QLineEdit()
        self.smtp_port.setPlaceholderText("587")
        smtp_layout.addRow("SMTP Port:", self.smtp_port)

        self.smtp_email = QLineEdit()
        self.smtp_email.setPlaceholderText("sender@example.com")
        smtp_layout.addRow("Sender Email:", self.smtp_email)

        self.smtp_password = QLineEdit()
        self.smtp_password.setEchoMode(QLineEdit.Password)
        self.smtp_password.setPlaceholderText("App password / SMTP password")
        smtp_layout.addRow("SMTP Password:", self.smtp_password)

        smtp_btns = QHBoxLayout()
        self.save_smtp_btn = QPushButton("Save SMTP Settings")
        self.save_smtp_btn.setProperty("class", "accent")
        self.save_smtp_btn.setCursor(Qt.PointingHandCursor)
        self.save_smtp_btn.clicked.connect(self._save_smtp)

        self.test_smtp_btn = QPushButton("Test Connection")
        self.test_smtp_btn.setProperty("class", "outline")
        self.test_smtp_btn.setCursor(Qt.PointingHandCursor)
        self.test_smtp_btn.clicked.connect(self._test_smtp)

        smtp_btns.addWidget(self.save_smtp_btn)
        smtp_btns.addWidget(self.test_smtp_btn)
        smtp_btns.addStretch()
        smtp_layout.addRow("", smtp_btns)

        smtp_group.setLayout(smtp_layout)
        layout.addWidget(smtp_group)

        # App Settings Group — card style
        app_group = QGroupBox("  \u2699  Application Settings")
        app_layout = QFormLayout()
        app_layout.setSpacing(12)

        self.company_name = QLineEdit()
        self.company_name.setPlaceholderText("Company / Organization name")
        app_layout.addRow("Company Name:", self.company_name)

        self.alert_enabled = QCheckBox("Enable automatic alert checking")
        app_layout.addRow("Alerts:", self.alert_enabled)

        save_app_btn = QPushButton("Save App Settings")
        save_app_btn.setProperty("class", "accent")
        save_app_btn.setCursor(Qt.PointingHandCursor)
        save_app_btn.clicked.connect(self._save_app_settings)
        app_layout.addRow("", save_app_btn)

        app_group.setLayout(app_layout)
        layout.addWidget(app_group)

        # Change Password Group — card style
        pwd_group = QGroupBox("  \U0001f512  Change My Password")
        pwd_layout = QFormLayout()
        pwd_layout.setSpacing(12)

        self.current_pwd = QLineEdit()
        self.current_pwd.setEchoMode(QLineEdit.Password)
        self.current_pwd.setPlaceholderText("Current password")
        pwd_layout.addRow("Current:", self.current_pwd)

        self.new_pwd = QLineEdit()
        self.new_pwd.setEchoMode(QLineEdit.Password)
        self.new_pwd.setPlaceholderText("New password")
        pwd_layout.addRow("New:", self.new_pwd)

        self.confirm_pwd = QLineEdit()
        self.confirm_pwd.setEchoMode(QLineEdit.Password)
        self.confirm_pwd.setPlaceholderText("Confirm new password")
        pwd_layout.addRow("Confirm:", self.confirm_pwd)

        change_pwd_btn = QPushButton("Change Password")
        change_pwd_btn.setProperty("class", "accent")
        change_pwd_btn.setCursor(Qt.PointingHandCursor)
        change_pwd_btn.clicked.connect(self._change_password)
        pwd_layout.addRow("", change_pwd_btn)

        pwd_group.setLayout(pwd_layout)
        layout.addWidget(pwd_group)

        layout.addStretch()

        scroll.setWidget(content)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def refresh_data(self):
        """Load current settings from the database."""
        session = Session()
        try:
            settings = {}
            for row in session.query(AppSetting).all():
                settings[row.key] = row.value

            self.smtp_server.setText(settings.get("smtp_server", ""))
            self.smtp_port.setText(settings.get("smtp_port", "587"))
            self.smtp_email.setText(settings.get("smtp_email", ""))
            self.smtp_password.setText(settings.get("smtp_password", ""))
            self.company_name.setText(settings.get("company_name", ""))
            self.alert_enabled.setChecked(
                settings.get("alert_check_enabled", "true").lower() == "true"
            )
        except Exception:
            pass
        finally:
            session.close()

    def _save_setting(self, key: str, value: str):
        session = Session()
        try:
            setting = session.query(AppSetting).filter_by(key=key).first()
            if setting:
                setting.value = value
                setting.updated_at = datetime.utcnow()
            else:
                setting = AppSetting(key=key, value=value, updated_at=datetime.utcnow())
                session.add(setting)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    def _save_smtp(self):
        self._save_setting("smtp_server", self.smtp_server.text().strip())
        self._save_setting("smtp_port", self.smtp_port.text().strip())
        self._save_setting("smtp_email", self.smtp_email.text().strip())
        self._save_setting("smtp_password", self.smtp_password.text())

        if self.current_user:
            self.log.log_activity(self.current_user.id, "settings_updated",
                                  "Updated SMTP settings")
        show_toast(self, "SMTP settings saved.", "success")

    def _test_smtp(self):
        email = self.smtp_email.text().strip()
        if not email:
            show_toast(self, "Enter an email address first.", "warning")
            return

        success = self.notification.send_email(
            email, "SWMS Test", "This is a test email from Smart Waste Management System."
        )
        if success:
            show_toast(self, "Test email sent successfully!", "success")
        else:
            show_toast(self, "Failed to send test email. Check your SMTP settings.", "error")

    def _save_app_settings(self):
        self._save_setting("company_name", self.company_name.text().strip())
        self._save_setting("alert_check_enabled",
                           "true" if self.alert_enabled.isChecked() else "false")

        if self.current_user:
            self.log.log_activity(self.current_user.id, "settings_updated",
                                  "Updated application settings")
        show_toast(self, "Application settings saved.", "success")

    def _change_password(self):
        if not self.current_user:
            return

        current = self.current_pwd.text()
        new = self.new_pwd.text()
        confirm = self.confirm_pwd.text()

        if not current or not new:
            show_toast(self, "Please fill in all password fields.", "error")
            return

        if new != confirm:
            show_toast(self, "New passwords do not match.", "error")
            return

        if len(new) < 4:
            show_toast(self, "Password must be at least 4 characters.", "error")
            return

        # Verify current password
        if not self.auth.verify_password(current, self.current_user.password_hash):
            show_toast(self, "Current password is incorrect.", "error")
            return

        new_hash = self.auth.hash_password(new)
        if self.auth.update_user(self.current_user.id, password_hash=new_hash):
            # Update in-memory user object
            self.current_user.password_hash = new_hash
            self.current_pwd.clear()
            self.new_pwd.clear()
            self.confirm_pwd.clear()
            self.log.log_activity(self.current_user.id, "password_changed",
                                  "Changed own password")
            show_toast(self, "Password changed successfully.", "success")
        else:
            show_toast(self, "Failed to change password.", "error")

    def set_user(self, user):
        self.current_user = user
