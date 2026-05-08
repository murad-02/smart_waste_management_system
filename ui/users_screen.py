from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QLineEdit, QComboBox, QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from config import USER_ROLES
from core.auth_manager import AuthManager
from core.log_manager import LogManager
from ui.widgets.toast import show_toast


class UserDialog(QDialog):
    """Dialog for creating or editing a user."""

    def __init__(self, user=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("Edit User" if user else "Create User")
        self.setMinimumWidth(420)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        if self.user:
            self.username_input.setText(self.user.username)
            self.username_input.setEnabled(False)
        layout.addRow("Username:", self.username_input)

        self.fullname_input = QLineEdit()
        self.fullname_input.setPlaceholderText("Full Name")
        if self.user:
            self.fullname_input.setText(self.user.full_name)
        layout.addRow("Full Name:", self.fullname_input)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email (optional)")
        if self.user and self.user.email:
            self.email_input.setText(self.user.email)
        layout.addRow("Email:", self.email_input)

        self.role_combo = QComboBox()
        for role in USER_ROLES:
            self.role_combo.addItem(role.capitalize(), role)
        if self.user:
            idx = self.role_combo.findData(self.user.role)
            if idx >= 0:
                self.role_combo.setCurrentIndex(idx)
        layout.addRow("Role:", self.role_combo)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("New password" if self.user else "Password")
        layout.addRow("Password:", self.password_input)

        if self.user:
            note = QLabel("Leave password blank to keep current password")
            note.setStyleSheet("color: #BFC5C9; font-size: 9pt;")
            layout.addRow("", note)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_data(self):
        return {
            "username": self.username_input.text().strip(),
            "full_name": self.fullname_input.text().strip(),
            "email": self.email_input.text().strip(),
            "role": self.role_combo.currentData(),
            "password": self.password_input.text()
        }


class UsersScreen(QWidget):
    """Admin screen for managing users with role badges."""

    ROLE_BADGE_COLORS = {
        "admin": ("#4CAF50", "#E5E5E5"),
        "supervisor": ("#64B5F6", "#1A1D1F"),
        "operator": ("#BFC5C9", "#1A1D1F"),
    }

    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.auth = AuthManager()
        self.log = LogManager()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()
        header = QLabel("User Management")
        header.setStyleSheet("font-size: 20pt; font-weight: bold; color: #E5E5E5;")
        header_layout.addWidget(header)
        header_layout.addStretch()

        self.add_btn = QPushButton("\u2795  Add User")
        self.add_btn.setProperty("class", "accent")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_user)
        header_layout.addWidget(self.add_btn)

        layout.addLayout(header_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Username", "Full Name", "Email", "Role", "Status", "Actions"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Fixed)          # ID
        header.setSectionResizeMode(4, QHeaderView.Fixed)          # Role
        header.setSectionResizeMode(5, QHeaderView.Fixed)          # Status
        header.setSectionResizeMode(6, QHeaderView.Fixed)          # Actions
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 90)
        self.table.setColumnWidth(6, 240)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(46)
        layout.addWidget(self.table)

    def refresh_data(self):
        users = self.auth.get_all_users()
        self.table.setRowCount(0)

        for user in users:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(user.id)))
            self.table.setItem(row, 1, QTableWidgetItem(user.username))
            self.table.setItem(row, 2, QTableWidgetItem(user.full_name))
            self.table.setItem(row, 3, QTableWidgetItem(user.email or ""))

            # Role badge — colored cell
            role_item = QTableWidgetItem(user.role.capitalize())
            role_colors = self.ROLE_BADGE_COLORS.get(user.role, ("#BFC5C9", "#1A1D1F"))
            role_item.setBackground(QColor(role_colors[0]))
            role_item.setForeground(QColor(role_colors[1]))
            self.table.setItem(row, 4, role_item)

            # Status badge — colored cell
            status_text = "Active" if user.is_active else "Inactive"
            status_item = QTableWidgetItem(status_text)
            if user.is_active:
                status_item.setBackground(QColor("#4CAF50"))
                status_item.setForeground(QColor("#E5E5E5"))
            else:
                status_item.setBackground(QColor("#E57373"))
                status_item.setForeground(QColor("#1A1D1F"))
            self.table.setItem(row, 5, status_item)

            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(6)
            actions_layout.setAlignment(Qt.AlignCenter)

            edit_btn = QPushButton("Edit")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setFixedHeight(30)
            edit_btn.setStyleSheet(
                "background-color: #2A2F33; color: #E5E5E5; border: 1px solid #3A3F44; "
                "border-radius: 4px; padding: 2px 12px; font-size: 10pt; min-height: 0px;"
            )
            edit_btn.clicked.connect(lambda _, u=user: self._edit_user(u))

            if user.is_active:
                toggle_btn = QPushButton("Deactivate")
                toggle_btn.setStyleSheet(
                    "background-color: #E57373; color: #1A1D1F; border: none; border-radius: 4px; "
                    "font-weight: bold; padding: 2px 12px; font-size: 10pt; min-height: 0px;"
                )
                toggle_btn.clicked.connect(lambda _, u=user: self._deactivate_user(u.id))
            else:
                toggle_btn = QPushButton("Activate")
                toggle_btn.setStyleSheet(
                    "background-color: #4CAF50; color: #E5E5E5; border: none; border-radius: 4px; "
                    "font-weight: bold; padding: 2px 12px; font-size: 10pt; min-height: 0px;"
                )
                toggle_btn.clicked.connect(lambda _, u=user: self._activate_user(u.id))

            toggle_btn.setFixedHeight(30)
            toggle_btn.setCursor(Qt.PointingHandCursor)

            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(toggle_btn)
            actions_layout.addStretch()

            self.table.setCellWidget(row, 6, actions_widget)

    def _add_user(self):
        dialog = UserDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data["username"] or not data["full_name"] or not data["password"]:
                show_toast(self, "Username, full name, and password are required.", "error")
                return

            result = self.auth.create_user(
                data["username"], data["password"], data["full_name"],
                data["email"], data["role"], self.current_user.id
            )
            if isinstance(result, str):
                show_toast(self, result, "error")
            else:
                self.log.log_activity(
                    self.current_user.id, "user_created",
                    f"Created user '{data['username']}' with role '{data['role']}'"
                )
                show_toast(self, f"User '{data['username']}' created.", "success")
                self.refresh_data()

    def _edit_user(self, user):
        dialog = UserDialog(user=user, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            kwargs = {
                "full_name": data["full_name"],
                "email": data["email"] if data["email"] else None,
                "role": data["role"]
            }
            if data["password"]:
                kwargs["password_hash"] = self.auth.hash_password(data["password"])

            if self.auth.update_user(user.id, **kwargs):
                self.log.log_activity(
                    self.current_user.id, "user_updated",
                    f"Updated user '{user.username}'"
                )
                show_toast(self, f"User '{user.username}' updated.", "success")
                self.refresh_data()
            else:
                show_toast(self, "Failed to update user.", "error")

    def _deactivate_user(self, user_id):
        result = self.auth.deactivate_user(user_id, self.current_user.id)
        if result is True:
            self.log.log_activity(self.current_user.id, "user_deactivated",
                                  f"Deactivated user #{user_id}")
            show_toast(self, "User deactivated.", "success")
            self.refresh_data()
        else:
            show_toast(self, str(result), "error")

    def _activate_user(self, user_id):
        if self.auth.activate_user(user_id):
            self.log.log_activity(self.current_user.id, "user_activated",
                                  f"Activated user #{user_id}")
            show_toast(self, "User activated.", "success")
            self.refresh_data()
        else:
            show_toast(self, "Failed to activate user.", "error")

    def set_user(self, user):
        self.current_user = user
