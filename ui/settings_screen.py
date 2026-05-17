import os
import shutil
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QFormLayout, QLineEdit, QGroupBox, QScrollArea, QCheckBox, QMessageBox,
    QDoubleSpinBox, QFileDialog, QDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QDateEdit, QComboBox, QAbstractItemView
)
from PyQt5.QtCore import Qt, QDate

from config import DATABASE_PATH
from database.db_setup import Session
from database.models import AppSetting
from core.auth_manager import AuthManager
from core.log_manager import LogManager
from core.notification_service import NotificationService
from ui.widgets.toast import show_toast


# ---------------------------------------------------------------------------
# Activity Log Viewer Dialog
# ---------------------------------------------------------------------------

class ActivityLogDialog(QDialog):
    """Dialog showing recent activity logs with date-range and user filters."""

    def __init__(self, log_manager: LogManager, auth_manager: AuthManager, parent=None):
        super().__init__(parent)
        self.log = log_manager
        self.auth = auth_manager

        self.setWindowTitle("Activity Logs")
        self.setMinimumSize(880, 520)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)

        title = QLabel("Activity Logs")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #E5E5E5;")
        outer.addWidget(title)

        # Filters row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        filter_row.addWidget(QLabel("User:"))
        self.user_combo = QComboBox()
        self.user_combo.addItem("All users", None)
        for u in self.auth.get_all_users():
            self.user_combo.addItem(f"{u.username} ({u.role})", u.id)
        filter_row.addWidget(self.user_combo)

        filter_row.addSpacing(12)
        filter_row.addWidget(QLabel("From:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        filter_row.addWidget(self.start_date)

        filter_row.addWidget(QLabel("To:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        filter_row.addWidget(self.end_date)

        self.apply_btn = QPushButton("Apply Filters")
        self.apply_btn.setProperty("class", "accent")
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.clicked.connect(self._reload)
        filter_row.addWidget(self.apply_btn)

        filter_row.addStretch()
        outer.addLayout(filter_row)

        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Time", "User", "Action", "Details"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        outer.addWidget(self.table)

        # Footer
        footer = QHBoxLayout()
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #8A9095;")
        footer.addWidget(self.count_label)
        footer.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        outer.addLayout(footer)

        # Cache usernames for fast row rendering
        self._user_names = {u.id: u.username for u in self.auth.get_all_users()}

        self._reload()

    def _reload(self):
        user_id = self.user_combo.currentData()
        start = datetime.combine(self.start_date.date().toPyDate(), datetime.min.time())
        end = datetime.combine(self.end_date.date().toPyDate(), datetime.max.time())

        logs = self.log.get_logs(
            user_id=user_id, start_date=start, end_date=end, limit=500
        )

        self.table.setRowCount(0)
        for row_idx, entry in enumerate(logs):
            self.table.insertRow(row_idx)
            ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else ""
            username = self._user_names.get(entry.user_id, f"user#{entry.user_id}")
            self.table.setItem(row_idx, 0, QTableWidgetItem(ts))
            self.table.setItem(row_idx, 1, QTableWidgetItem(username))
            self.table.setItem(row_idx, 2, QTableWidgetItem(entry.action or ""))
            self.table.setItem(row_idx, 3, QTableWidgetItem(entry.details or ""))

        self.count_label.setText(f"{len(logs)} log entr{'y' if len(logs) == 1 else 'ies'}")


# ---------------------------------------------------------------------------
# Settings Screen
# ---------------------------------------------------------------------------

class SettingsScreen(QWidget):
    """Admin settings screen for SMTP, app, detection, maintenance and password."""

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
        header.setStyleSheet("font-size: 20pt; font-weight: bold; color: #E5E5E5;")
        layout.addWidget(header)

        layout.addWidget(self._build_smtp_group())
        layout.addWidget(self._build_app_group())
        layout.addWidget(self._build_detection_group())
        layout.addWidget(self._build_maintenance_group())
        layout.addWidget(self._build_password_group())

        layout.addStretch()

        scroll.setWidget(content)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    # --- SMTP -------------------------------------------------------------

    def _build_smtp_group(self):
        group = QGroupBox("  ✉  Email / SMTP Configuration")
        form = QFormLayout()
        form.setSpacing(12)

        self.smtp_server = QLineEdit()
        self.smtp_server.setPlaceholderText("e.g., smtp.gmail.com")
        form.addRow("SMTP Server:", self.smtp_server)

        self.smtp_port = QLineEdit()
        self.smtp_port.setPlaceholderText("587")
        form.addRow("SMTP Port:", self.smtp_port)

        self.smtp_email = QLineEdit()
        self.smtp_email.setPlaceholderText("sender@example.com")
        form.addRow("Sender Email:", self.smtp_email)

        self.smtp_password = QLineEdit()
        self.smtp_password.setEchoMode(QLineEdit.Password)
        self.smtp_password.setPlaceholderText("App password / SMTP password")
        form.addRow("SMTP Password:", self.smtp_password)

        btns = QHBoxLayout()
        self.save_smtp_btn = QPushButton("Save SMTP Settings")
        self.save_smtp_btn.setProperty("class", "accent")
        self.save_smtp_btn.setCursor(Qt.PointingHandCursor)
        self.save_smtp_btn.clicked.connect(self._save_smtp)

        self.test_smtp_btn = QPushButton("Test Connection")
        self.test_smtp_btn.setProperty("class", "outline")
        self.test_smtp_btn.setCursor(Qt.PointingHandCursor)
        self.test_smtp_btn.clicked.connect(self._test_smtp)

        btns.addWidget(self.save_smtp_btn)
        btns.addWidget(self.test_smtp_btn)
        btns.addStretch()
        form.addRow("", btns)

        group.setLayout(form)
        return group

    # --- General app settings --------------------------------------------

    def _build_app_group(self):
        group = QGroupBox("  ⚙  Application Settings")
        form = QFormLayout()
        form.setSpacing(12)

        self.company_name = QLineEdit()
        self.company_name.setPlaceholderText("Company / Organization name")
        form.addRow("Company Name:", self.company_name)

        self.alert_enabled = QCheckBox("Enable automatic alert checking")
        form.addRow("Alerts:", self.alert_enabled)

        save_btn = QPushButton("Save App Settings")
        save_btn.setProperty("class", "accent")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save_app_settings)
        form.addRow("", save_btn)

        group.setLayout(form)
        return group

    # --- Detection settings ----------------------------------------------

    def _build_detection_group(self):
        group = QGroupBox("  \U0001f50d  Detection Settings")
        form = QFormLayout()
        form.setSpacing(12)

        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.05, 0.95)
        self.confidence_spin.setSingleStep(0.05)
        self.confidence_spin.setDecimals(2)
        self.confidence_spin.setValue(0.30)
        self.confidence_spin.setSuffix("   (0.05 – 0.95)")
        form.addRow("Default Confidence Threshold:", self.confidence_spin)

        hint = QLabel(
            "Lower values detect more bins but produce more false positives. "
            "Default is 0.30."
        )
        hint.setStyleSheet("color: #8A9095; font-size: 9pt;")
        hint.setWordWrap(True)
        form.addRow("", hint)

        save_btn = QPushButton("Save Detection Settings")
        save_btn.setProperty("class", "accent")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save_detection_settings)
        form.addRow("", save_btn)

        group.setLayout(form)
        return group

    # --- Maintenance: backup + activity log -------------------------------

    def _build_maintenance_group(self):
        group = QGroupBox("  \U0001f6e0  Maintenance")
        v = QVBoxLayout()
        v.setSpacing(10)

        # Backup row
        backup_row = QHBoxLayout()
        backup_label = QLabel("Export a copy of the SQLite database to a file of your choice.")
        backup_label.setStyleSheet("color: #BFC5C9;")
        backup_label.setWordWrap(True)
        backup_btn = QPushButton("Export Database Backup")
        backup_btn.setProperty("class", "accent")
        backup_btn.setCursor(Qt.PointingHandCursor)
        backup_btn.clicked.connect(self._export_backup)
        backup_row.addWidget(backup_label, 1)
        backup_row.addWidget(backup_btn)
        v.addLayout(backup_row)

        # Logs row
        logs_row = QHBoxLayout()
        logs_label = QLabel("Browse activity logs (login, detection, settings changes, etc.).")
        logs_label.setStyleSheet("color: #BFC5C9;")
        logs_label.setWordWrap(True)
        logs_btn = QPushButton("View Activity Logs")
        logs_btn.setProperty("class", "outline")
        logs_btn.setCursor(Qt.PointingHandCursor)
        logs_btn.clicked.connect(self._open_activity_logs)
        logs_row.addWidget(logs_label, 1)
        logs_row.addWidget(logs_btn)
        v.addLayout(logs_row)

        group.setLayout(v)
        return group

    # --- Change password --------------------------------------------------

    def _build_password_group(self):
        group = QGroupBox("  \U0001f512  Change My Password")
        form = QFormLayout()
        form.setSpacing(12)

        self.current_pwd = QLineEdit()
        self.current_pwd.setEchoMode(QLineEdit.Password)
        self.current_pwd.setPlaceholderText("Current password")
        form.addRow("Current:", self.current_pwd)

        self.new_pwd = QLineEdit()
        self.new_pwd.setEchoMode(QLineEdit.Password)
        self.new_pwd.setPlaceholderText("New password")
        form.addRow("New:", self.new_pwd)

        self.confirm_pwd = QLineEdit()
        self.confirm_pwd.setEchoMode(QLineEdit.Password)
        self.confirm_pwd.setPlaceholderText("Confirm new password")
        form.addRow("Confirm:", self.confirm_pwd)

        change_btn = QPushButton("Change Password")
        change_btn.setProperty("class", "accent")
        change_btn.setCursor(Qt.PointingHandCursor)
        change_btn.clicked.connect(self._change_password)
        form.addRow("", change_btn)

        group.setLayout(form)
        return group

    # ---------------- Data: load / save ----------------

    def refresh_data(self):
        """Load current settings from the database."""
        session = Session()
        try:
            settings = {row.key: row.value for row in session.query(AppSetting).all()}
        except Exception:
            settings = {}
        finally:
            session.close()

        self.smtp_server.setText(settings.get("smtp_server", ""))
        self.smtp_port.setText(settings.get("smtp_port", "587"))
        self.smtp_email.setText(settings.get("smtp_email", ""))
        self.smtp_password.setText(settings.get("smtp_password", ""))
        self.company_name.setText(settings.get("company_name", ""))
        self.alert_enabled.setChecked(
            settings.get("alert_check_enabled", "true").lower() == "true"
        )
        try:
            self.confidence_spin.setValue(
                float(settings.get("detection_confidence_threshold", "0.30"))
            )
        except (TypeError, ValueError):
            self.confidence_spin.setValue(0.30)

        # Clear password fields on each load
        self.current_pwd.clear()
        self.new_pwd.clear()
        self.confirm_pwd.clear()

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

        # Save current form values before testing so verbose-send reads the latest
        self._save_setting("smtp_server", self.smtp_server.text().strip())
        self._save_setting("smtp_port", self.smtp_port.text().strip())
        self._save_setting("smtp_email", email)
        self._save_setting("smtp_password", self.smtp_password.text())

        success, error = self.notification.send_email_verbose(
            email, "SWMS Test", "This is a test email from Smart Waste Management System."
        )
        if success:
            show_toast(self, "Test email sent successfully!", "success")
        else:
            # Show the real error in a dialog (toast can't fit long messages)
            QMessageBox.critical(self, "SMTP Test Failed", error or "Unknown error.")

    def _save_app_settings(self):
        self._save_setting("company_name", self.company_name.text().strip())
        self._save_setting("alert_check_enabled",
                           "true" if self.alert_enabled.isChecked() else "false")

        if self.current_user:
            self.log.log_activity(self.current_user.id, "settings_updated",
                                  "Updated application settings")
        show_toast(self, "Application settings saved.", "success")

    def _save_detection_settings(self):
        value = round(float(self.confidence_spin.value()), 2)
        self._save_setting("detection_confidence_threshold", f"{value:.2f}")
        if self.current_user:
            self.log.log_activity(
                self.current_user.id, "settings_updated",
                f"Set detection confidence threshold to {value:.2f}"
            )
        show_toast(self, f"Detection threshold set to {value:.2f}.", "success")

    # --- Maintenance handlers --------------------------------------------

    def _export_backup(self):
        if not os.path.isfile(DATABASE_PATH):
            show_toast(self, "Database file not found.", "error")
            return

        default_name = f"swms_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Database Backup", default_name,
            "SQLite Database (*.db);;All Files (*)"
        )
        if not file_path:
            return

        try:
            shutil.copy2(DATABASE_PATH, file_path)
        except Exception as e:
            show_toast(self, f"Backup failed: {e}", "error")
            return

        if self.current_user:
            self.log.log_activity(
                self.current_user.id, "database_backup",
                f"Exported database backup to {file_path}"
            )
        QMessageBox.information(
            self, "Backup Complete",
            f"Database backed up to:\n{file_path}"
        )

    def _open_activity_logs(self):
        dlg = ActivityLogDialog(self.log, self.auth, parent=self)
        dlg.exec_()

    # --- Password ---------------------------------------------------------

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

        if not self.auth.verify_password(current, self.current_user.password_hash):
            show_toast(self, "Current password is incorrect.", "error")
            return

        new_hash = self.auth.hash_password(new)
        if self.auth.update_user(self.current_user.id, password_hash=new_hash):
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
