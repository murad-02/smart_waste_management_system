from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QLineEdit, QComboBox, QSpinBox, QDialogButtonBox, QTabWidget,
    QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from config import WASTE_CATEGORIES
from core.alert_manager import AlertManager
from core.log_manager import LogManager
from ui.widgets.toast import show_toast


class AlertRuleDialog(QDialog):
    """Dialog for creating/editing an alert rule."""

    def __init__(self, rule=None, parent=None):
        super().__init__(parent)
        self.rule = rule
        self.setWindowTitle("Edit Rule" if rule else "Create Alert Rule")
        self.setMinimumWidth(420)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., High Plastic Alert")
        if self.rule:
            self.name_input.setText(self.rule.rule_name)
        layout.addRow("Rule Name:", self.name_input)

        self.category_combo = QComboBox()
        for cat in WASTE_CATEGORIES:
            self.category_combo.addItem(cat, cat)
        if self.rule:
            idx = self.category_combo.findData(self.rule.category)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
        layout.addRow("Category:", self.category_combo)

        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 10000)
        self.threshold_spin.setValue(10)
        if self.rule:
            self.threshold_spin.setValue(self.rule.threshold_value)
        layout.addRow("Threshold:", self.threshold_spin)

        self.period_combo = QComboBox()
        for period in ["daily", "weekly", "monthly"]:
            self.period_combo.addItem(period.capitalize(), period)
        if self.rule:
            idx = self.period_combo.findData(self.rule.period)
            if idx >= 0:
                self.period_combo.setCurrentIndex(idx)
        layout.addRow("Period:", self.period_combo)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("notification@example.com (optional)")
        if self.rule and self.rule.notify_email:
            self.email_input.setText(self.rule.notify_email)
        layout.addRow("Notify Email:", self.email_input)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_data(self):
        return {
            "rule_name": self.name_input.text().strip(),
            "category": self.category_combo.currentData(),
            "threshold_value": self.threshold_spin.value(),
            "period": self.period_combo.currentData(),
            "notify_email": self.email_input.text().strip()
        }


class AlertsScreen(QWidget):
    """Screen with tabs for alert rules and triggered alerts."""

    SEVERITY_COLORS = {
        "critical": ("#E57373", "#1A1D1F"),
        "warning": ("#FFC107", "#1A1D1F"),
        "info": ("#64B5F6", "#1A1D1F"),
    }

    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.alert_mgr = AlertManager()
        self.log = LogManager()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QLabel("Alerts & Rules")
        header.setStyleSheet("font-size: 20pt; font-weight: bold; color: #E5E5E5;")
        layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()

        # --- Triggered Alerts Tab ---
        alerts_widget = QWidget()
        alerts_layout = QVBoxLayout(alerts_widget)
        alerts_layout.setContentsMargins(0, 12, 0, 0)

        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(5)
        self.alerts_table.setHorizontalHeaderLabels([
            "ID", "Message", "Severity", "Triggered At", "Actions"
        ])
        a_header = self.alerts_table.horizontalHeader()
        a_header.setSectionResizeMode(QHeaderView.Stretch)
        a_header.setSectionResizeMode(0, QHeaderView.Fixed)        # ID
        a_header.setSectionResizeMode(2, QHeaderView.Fixed)        # Severity
        a_header.setSectionResizeMode(4, QHeaderView.Fixed)        # Actions
        self.alerts_table.setColumnWidth(0, 50)
        self.alerts_table.setColumnWidth(2, 90)
        self.alerts_table.setColumnWidth(4, 130)
        self.alerts_table.setAlternatingRowColors(True)
        self.alerts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.alerts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.alerts_table.verticalHeader().setVisible(False)
        self.alerts_table.verticalHeader().setDefaultSectionSize(46)
        alerts_layout.addWidget(self.alerts_table)

        self.tabs.addTab(alerts_widget, "\u26a0  Triggered Alerts")

        # --- Alert Rules Tab ---
        rules_widget = QWidget()
        rules_layout = QVBoxLayout(rules_widget)
        rules_layout.setContentsMargins(0, 12, 0, 0)

        rules_header = QHBoxLayout()
        rules_header.addStretch()
        self.add_rule_btn = QPushButton("\u2795  Add Rule")
        self.add_rule_btn.setProperty("class", "accent")
        self.add_rule_btn.setCursor(Qt.PointingHandCursor)
        self.add_rule_btn.clicked.connect(self._add_rule)
        rules_header.addWidget(self.add_rule_btn)
        rules_layout.addLayout(rules_header)

        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(7)
        self.rules_table.setHorizontalHeaderLabels([
            "ID", "Name", "Category", "Threshold", "Period", "Active", "Actions"
        ])
        r_header = self.rules_table.horizontalHeader()
        r_header.setSectionResizeMode(QHeaderView.Stretch)
        r_header.setSectionResizeMode(0, QHeaderView.Fixed)        # ID
        r_header.setSectionResizeMode(3, QHeaderView.Fixed)        # Threshold
        r_header.setSectionResizeMode(5, QHeaderView.Fixed)        # Active
        r_header.setSectionResizeMode(6, QHeaderView.Fixed)        # Actions
        self.rules_table.setColumnWidth(0, 50)
        self.rules_table.setColumnWidth(3, 80)
        self.rules_table.setColumnWidth(5, 70)
        self.rules_table.setColumnWidth(6, 200)
        self.rules_table.setAlternatingRowColors(True)
        self.rules_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.rules_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.rules_table.verticalHeader().setVisible(False)
        self.rules_table.verticalHeader().setDefaultSectionSize(46)
        rules_layout.addWidget(self.rules_table)

        self.tabs.addTab(rules_widget, "\U0001f4cb  Alert Rules")

        layout.addWidget(self.tabs)

    def refresh_data(self):
        self._load_alerts()
        self._load_rules()

    def _load_alerts(self):
        alerts = self.alert_mgr.get_alerts(acknowledged=False)
        self.alerts_table.setRowCount(0)

        for alert in alerts:
            row = self.alerts_table.rowCount()
            self.alerts_table.insertRow(row)

            self.alerts_table.setItem(row, 0, QTableWidgetItem(str(alert.id)))
            self.alerts_table.setItem(row, 1, QTableWidgetItem(alert.message))

            # Severity badge — colored cell
            severity_item = QTableWidgetItem(alert.severity.capitalize())
            colors = self.SEVERITY_COLORS.get(alert.severity, ("#BFC5C9", "#1A1D1F"))
            severity_item.setBackground(QColor(colors[0]))
            severity_item.setForeground(QColor(colors[1]))
            self.alerts_table.setItem(row, 2, severity_item)

            self.alerts_table.setItem(row, 3, QTableWidgetItem(
                alert.triggered_at.strftime("%Y-%m-%d %H:%M") if alert.triggered_at else ""
            ))

            # Acknowledge button
            ack_widget = QWidget()
            ack_layout = QHBoxLayout(ack_widget)
            ack_layout.setContentsMargins(4, 4, 4, 4)
            ack_layout.setAlignment(Qt.AlignCenter)

            ack_btn = QPushButton("\u2714 Ack")
            ack_btn.setFixedHeight(30)
            ack_btn.setStyleSheet(
                "background-color: #52796A; color: #E5E5E5; border: none; border-radius: 4px; "
                "padding: 2px 12px; font-weight: bold; font-size: 10pt; min-height: 0px;"
            )
            ack_btn.setCursor(Qt.PointingHandCursor)
            ack_btn.clicked.connect(lambda _, a=alert: self._acknowledge(a.id))
            
            ack_layout.addWidget(ack_btn)
            self.alerts_table.setCellWidget(row, 4, ack_widget)

    def _load_rules(self):
        rules = self.alert_mgr.get_all_rules()
        self.rules_table.setRowCount(0)

        for rule in rules:
            row = self.rules_table.rowCount()
            self.rules_table.insertRow(row)

            self.rules_table.setItem(row, 0, QTableWidgetItem(str(rule.id)))
            self.rules_table.setItem(row, 1, QTableWidgetItem(rule.rule_name))
            self.rules_table.setItem(row, 2, QTableWidgetItem(rule.category))
            self.rules_table.setItem(row, 3, QTableWidgetItem(str(rule.threshold_value)))
            self.rules_table.setItem(row, 4, QTableWidgetItem(rule.period.capitalize()))

            # Active status badge
            active_item = QTableWidgetItem("Yes" if rule.is_active else "No")
            if rule.is_active:
                active_item.setBackground(QColor("#4CAF50"))
                active_item.setForeground(QColor("#E5E5E5"))
            else:
                active_item.setBackground(QColor("#E57373"))
                active_item.setForeground(QColor("#1A1D1F"))
            self.rules_table.setItem(row, 5, active_item)

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
            edit_btn.clicked.connect(lambda _, r=rule: self._edit_rule(r))

            delete_btn = QPushButton("\U0001f5d1")
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.setFixedSize(34, 30)
            delete_btn.setStyleSheet(
                "background-color: #E57373; color: #1A1D1F; border: none; border-radius: 4px; "
                "font-weight: bold; padding: 0px; font-size: 11pt; min-height: 0px;"
            )
            delete_btn.clicked.connect(lambda _, r=rule: self._delete_rule(r.id))

            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            actions_layout.addStretch()
            self.rules_table.setCellWidget(row, 6, actions_widget)

    def _acknowledge(self, alert_id):
        if not self.current_user:
            return
        if self.alert_mgr.acknowledge_alert(alert_id, self.current_user.id):
            self.log.log_activity(self.current_user.id, "alert_acknowledged",
                                  f"Acknowledged alert #{alert_id}")
            show_toast(self, "Alert acknowledged.", "success")
            self.refresh_data()

    def _add_rule(self):
        dialog = AlertRuleDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data["rule_name"]:
                show_toast(self, "Rule name is required.", "error")
                return
            rule = self.alert_mgr.create_rule(
                data["rule_name"], data["category"], data["threshold_value"],
                data["period"], data["notify_email"], self.current_user.id
            )
            if rule:
                self.log.log_activity(self.current_user.id, "rule_created",
                                      f"Created alert rule '{data['rule_name']}'")
                show_toast(self, "Alert rule created.", "success")
                self.refresh_data()
            else:
                show_toast(self, "Failed to create rule.", "error")

    def _edit_rule(self, rule):
        dialog = AlertRuleDialog(rule=rule, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if self.alert_mgr.update_rule(rule.id, **data):
                self.log.log_activity(self.current_user.id, "rule_updated",
                                      f"Updated alert rule '{data['rule_name']}'")
                show_toast(self, "Rule updated.", "success")
                self.refresh_data()
            else:
                show_toast(self, "Failed to update rule.", "error")

    def _delete_rule(self, rule_id):
        reply = QMessageBox.question(
            self, "Confirm", f"Delete alert rule #{rule_id}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.alert_mgr.delete_rule(rule_id):
                self.log.log_activity(self.current_user.id, "rule_deleted",
                                      f"Deleted alert rule #{rule_id}")
                show_toast(self, "Rule deleted.", "success")
                self.refresh_data()

    def set_user(self, user):
        self.current_user = user
