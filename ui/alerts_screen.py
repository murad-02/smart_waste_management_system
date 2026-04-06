from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QLineEdit, QComboBox, QSpinBox, QDialogButtonBox, QTabWidget,
    QMessageBox
)
from PyQt5.QtCore import Qt

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
        self.setMinimumWidth(400)
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
        header.setStyleSheet("font-size: 20pt; font-weight: bold; color: #e0e0e0;")
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
        self.alerts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.alerts_table.setAlternatingRowColors(True)
        self.alerts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.alerts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.alerts_table.verticalHeader().setVisible(False)
        alerts_layout.addWidget(self.alerts_table)

        self.tabs.addTab(alerts_widget, "Triggered Alerts")

        # --- Alert Rules Tab ---
        rules_widget = QWidget()
        rules_layout = QVBoxLayout(rules_widget)
        rules_layout.setContentsMargins(0, 12, 0, 0)

        rules_header = QHBoxLayout()
        rules_header.addStretch()
        self.add_rule_btn = QPushButton("+ Add Rule")
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
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rules_table.setAlternatingRowColors(True)
        self.rules_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.rules_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.rules_table.verticalHeader().setVisible(False)
        rules_layout.addWidget(self.rules_table)

        self.tabs.addTab(rules_widget, "Alert Rules")

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

            severity_item = QTableWidgetItem(alert.severity.capitalize())
            if alert.severity == "critical":
                severity_item.setForeground(Qt.red)
            elif alert.severity == "warning":
                severity_item.setForeground(Qt.yellow)
            else:
                severity_item.setForeground(Qt.cyan)
            self.alerts_table.setItem(row, 2, severity_item)

            self.alerts_table.setItem(row, 3, QTableWidgetItem(
                alert.triggered_at.strftime("%Y-%m-%d %H:%M") if alert.triggered_at else ""
            ))

            # Acknowledge button
            ack_btn = QPushButton("Acknowledge")
            ack_btn.setStyleSheet("background-color: #00b894; color: white; border-radius: 4px;")
            ack_btn.setCursor(Qt.PointingHandCursor)
            ack_btn.clicked.connect(lambda _, a=alert: self._acknowledge(a.id))
            self.alerts_table.setCellWidget(row, 4, ack_btn)

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

            active_item = QTableWidgetItem("Yes" if rule.is_active else "No")
            active_item.setForeground(Qt.green if rule.is_active else Qt.red)
            self.rules_table.setItem(row, 5, active_item)

            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)

            edit_btn = QPushButton("Edit")
            edit_btn.setFixedSize(50, 28)
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.clicked.connect(lambda _, r=rule: self._edit_rule(r))

            delete_btn = QPushButton("\U0001f5d1")
            delete_btn.setFixedSize(28, 28)
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.setStyleSheet("background-color: #d63031; color: white; border-radius: 4px;")
            delete_btn.clicked.connect(lambda _, r=rule: self._delete_rule(r.id))

            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
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
