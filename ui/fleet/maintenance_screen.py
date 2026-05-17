"""Maintenance log + upcoming-service screen."""

from datetime import date

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QComboBox, QDoubleSpinBox, QDateEdit,
    QTextEdit, QDialogButtonBox, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor

from core.fleet.maintenance_service import MaintenanceService
from core.fleet.truck_service import TruckService
from core.fleet.constants import SERVICE_TYPES, MAINTENANCE_DUE_DAYS, pretty
from core.fleet.fleet_permissions import can
from ui.widgets.toast import show_toast
from ui.fleet._common import (
    build_header, primary_button, secondary_button, danger_button
)


class MaintenanceDialog(QDialog):
    def __init__(self, record=None, trucks=None, parent=None):
        super().__init__(parent)
        self.record = record
        self.trucks = trucks or []
        self.setWindowTitle("Edit Maintenance" if record else "Log Maintenance")
        self.setMinimumWidth(460)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        self.truck_combo = QComboBox()
        for t in self.trucks:
            self.truck_combo.addItem(f"{t.truck_code} ({t.plate_number})", t.id)
        if self.record:
            i = self.truck_combo.findData(self.record.truck_id)
            if i >= 0:
                self.truck_combo.setCurrentIndex(i)
            self.truck_combo.setEnabled(False)
        layout.addRow("Truck:", self.truck_combo)

        self.type_combo = QComboBox()
        for st in SERVICE_TYPES:
            self.type_combo.addItem(pretty(st), st)
        if self.record:
            i = self.type_combo.findData(self.record.service_type)
            if i >= 0:
                self.type_combo.setCurrentIndex(i)
        layout.addRow("Service Type:", self.type_combo)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd")
        if self.record:
            d = self.record.service_date
            self.date_input.setDate(QDate(d.year, d.month, d.day))
        else:
            self.date_input.setDate(QDate.currentDate())
        layout.addRow("Service Date:", self.date_input)

        self.next_date_input = QDateEdit()
        self.next_date_input.setCalendarPopup(True)
        self.next_date_input.setDisplayFormat("yyyy-MM-dd")
        if self.record and self.record.next_service_date:
            d = self.record.next_service_date
            self.next_date_input.setDate(QDate(d.year, d.month, d.day))
        else:
            self.next_date_input.setDate(QDate.currentDate().addMonths(3))
        layout.addRow("Next Service:", self.next_date_input)

        self.cost_input = QDoubleSpinBox()
        self.cost_input.setPrefix("$ ")
        self.cost_input.setRange(0.0, 1_000_000.0)
        self.cost_input.setDecimals(2)
        if self.record and self.record.cost:
            self.cost_input.setValue(float(self.record.cost))
        layout.addRow("Cost:", self.cost_input)

        self.notes_input = QTextEdit(self.record.notes if self.record else "")
        self.notes_input.setFixedHeight(70)
        layout.addRow("Notes:", self.notes_input)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_data(self) -> dict:
        sd = self.date_input.date()
        nd = self.next_date_input.date()
        return {
            "truck_id": self.truck_combo.currentData(),
            "service_type": self.type_combo.currentData(),
            "service_date": date(sd.year(), sd.month(), sd.day()),
            "next_service_date": date(nd.year(), nd.month(), nd.day()),
            "cost": self.cost_input.value(),
            "notes": self.notes_input.toPlainText(),
        }


class MaintenanceScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_user = None
        self.service = MaintenanceService()
        self.truck_service = TruckService()
        self._build_ui()

    def set_user(self, user):
        self.current_user = user
        self.add_btn.setEnabled(can(user, "maintenance.create"))

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_row = build_header("Maintenance",
                                  "Service logs & upcoming jobs")
        self.add_btn = primary_button("➕  Log Service")
        self.add_btn.clicked.connect(self._add)
        header_row.addWidget(self.add_btn)
        layout.addLayout(header_row)

        # Due-soon banner
        self.due_banner = self._build_due_banner()
        layout.addWidget(self.due_banner)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Truck", "Service", "Date", "Next Service",
             "Cost", "Notes", "Actions"]
        )
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        for col, w in [(0, 50), (3, 110), (4, 120), (5, 100), (7, 180)]:
            h.setSectionResizeMode(col, QHeaderView.Fixed)
            self.table.setColumnWidth(col, w)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(42)
        layout.addWidget(self.table)

    def _build_due_banner(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background-color: #2A2620; border: 1px solid #FFC107; "
            "border-radius: 8px; padding: 6px; }"
        )
        h = QHBoxLayout(frame)
        h.setContentsMargins(14, 8, 14, 8)
        icon = QLabel("⚠️")
        icon.setStyleSheet("font-size: 14pt; background: transparent;")
        h.addWidget(icon)
        self.due_label = QLabel("Loading…")
        self.due_label.setStyleSheet("color: #FFC107; font-size: 11pt; "
                                     "background: transparent;")
        h.addWidget(self.due_label)
        h.addStretch()
        frame.hide()
        return frame

    # ------------------------------------------------------------------
    def refresh_data(self):
        if self.current_user is None:
            return
        try:
            records = self.service.list_records()
            due = self.service.list_due(days=MAINTENANCE_DUE_DAYS)
        except Exception as exc:
            show_toast(self, f"Failed to load maintenance: {exc}", "error")
            return

        if due:
            codes = ", ".join(sorted({r.truck.truck_code for r in due
                                      if r.truck}))
            self.due_label.setText(
                f"{len(due)} truck(s) due for service within "
                f"{MAINTENANCE_DUE_DAYS} days: {codes}"
            )
            self.due_banner.show()
        else:
            self.due_banner.hide()

        self.table.setRowCount(0)
        today = date.today()
        for r in records:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(r.id)))
            self.table.setItem(row, 1, QTableWidgetItem(
                r.truck.truck_code if r.truck else "—"))
            self.table.setItem(row, 2, QTableWidgetItem(pretty(r.service_type)))
            self.table.setItem(row, 3, QTableWidgetItem(str(r.service_date)))

            next_item = QTableWidgetItem(
                str(r.next_service_date) if r.next_service_date else "—"
            )
            if r.next_service_date and r.next_service_date <= today:
                next_item.setForeground(QColor("#E57373"))
            elif r.next_service_date and (r.next_service_date - today).days <= MAINTENANCE_DUE_DAYS:
                next_item.setForeground(QColor("#FFC107"))
            self.table.setItem(row, 4, next_item)

            self.table.setItem(row, 5,
                               QTableWidgetItem(f"${r.cost:.2f}" if r.cost else "—"))
            self.table.setItem(row, 6, QTableWidgetItem(r.notes or "—"))
            self.table.setCellWidget(row, 7, self._row_actions(r))

    def _row_actions(self, record) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(4, 4, 4, 4)
        h.setSpacing(6)
        h.setAlignment(Qt.AlignCenter)

        edit = secondary_button("Edit")
        edit.setEnabled(can(self.current_user, "maintenance.edit"))
        edit.clicked.connect(lambda _, r=record: self._edit(r))
        h.addWidget(edit)

        delete = danger_button("Delete")
        delete.setEnabled(can(self.current_user, "maintenance.delete"))
        delete.clicked.connect(lambda _, rid=record.id: self._delete(rid))
        h.addWidget(delete)
        return w

    # ------------------------------------------------------------------
    def _add(self):
        if not can(self.current_user, "maintenance.create"):
            show_toast(self, "Permission denied.", "error")
            return
        trucks = self.truck_service.list_trucks()
        if not trucks:
            show_toast(self, "Add a truck before logging maintenance.", "warning")
            return
        dialog = MaintenanceDialog(trucks=trucks, parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return
        try:
            self.service.create(self.current_user, dialog.get_data())
            show_toast(self, "Service logged.", "success")
            self.refresh_data()
        except Exception as exc:
            show_toast(self, str(exc), "error")

    def _edit(self, record):
        trucks = self.truck_service.list_trucks()
        dialog = MaintenanceDialog(record=record, trucks=trucks, parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return
        try:
            self.service.update(self.current_user, record.id, dialog.get_data())
            show_toast(self, "Maintenance updated.", "success")
            self.refresh_data()
        except Exception as exc:
            show_toast(self, str(exc), "error")

    def _delete(self, record_id: int):
        confirm = QMessageBox.question(
            self, "Delete Maintenance Record",
            f"Permanently delete maintenance #{record_id}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self.service.delete(self.current_user, record_id)
            show_toast(self, "Record deleted.", "success")
            self.refresh_data()
        except Exception as exc:
            show_toast(self, str(exc), "error")
