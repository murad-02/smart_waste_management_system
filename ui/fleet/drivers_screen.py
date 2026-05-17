"""Drivers CRUD screen."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox,
    QMessageBox
)
from PyQt5.QtCore import Qt

from core.fleet.driver_service import DriverService
from core.fleet.truck_service import TruckService
from core.fleet.constants import DRIVER_STATUSES, pretty
from core.fleet.fleet_permissions import can
from ui.widgets.toast import show_toast
from ui.fleet._common import (
    build_header, primary_button, secondary_button, danger_button,
    filter_bar, status_item
)


class DriverDialog(QDialog):
    def __init__(self, driver=None, trucks=None, parent=None):
        super().__init__(parent)
        self.driver = driver
        self.trucks = trucks or []
        self.setWindowTitle("Edit Driver" if driver else "Add Driver")
        self.setMinimumWidth(460)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        self.name_input = QLineEdit(self.driver.name if self.driver else "")
        layout.addRow("Full Name:", self.name_input)

        self.phone_input = QLineEdit(self.driver.phone if self.driver else "")
        self.phone_input.setPlaceholderText("+880 17… (optional)")
        layout.addRow("Phone:", self.phone_input)

        self.email_input = QLineEdit(self.driver.email if self.driver else "")
        self.email_input.setPlaceholderText("optional")
        layout.addRow("Email:", self.email_input)

        self.license_input = QLineEdit(self.driver.license_number if self.driver else "")
        layout.addRow("License No.:", self.license_input)

        self.truck_combo = QComboBox()
        self.truck_combo.addItem("— Unassigned —", None)
        for t in self.trucks:
            self.truck_combo.addItem(f"{t.truck_code} ({t.plate_number})", t.id)
        if self.driver and self.driver.assigned_truck_id:
            i = self.truck_combo.findData(self.driver.assigned_truck_id)
            if i >= 0:
                self.truck_combo.setCurrentIndex(i)
        layout.addRow("Assigned Truck:", self.truck_combo)

        self.status_combo = QComboBox()
        for s in DRIVER_STATUSES:
            self.status_combo.addItem(pretty(s), s)
        if self.driver:
            i = self.status_combo.findData(self.driver.status)
            if i >= 0:
                self.status_combo.setCurrentIndex(i)
        layout.addRow("Status:", self.status_combo)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_data(self) -> dict:
        return {
            "name": self.name_input.text(),
            "phone": self.phone_input.text(),
            "email": self.email_input.text(),
            "license_number": self.license_input.text(),
            "assigned_truck_id": self.truck_combo.currentData(),
            "status": self.status_combo.currentData(),
        }


class DriversScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_user = None
        self.service = DriverService()
        self.truck_service = TruckService()
        self._build_ui()

    def set_user(self, user):
        self.current_user = user
        self.add_btn.setEnabled(can(user, "driver.create"))

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_row = build_header("Driver Management",
                                  "Personnel & truck assignments")
        self.add_btn = primary_button("➕  Add Driver")
        self.add_btn.clicked.connect(self._add)
        header_row.addWidget(self.add_btn)
        layout.addLayout(header_row)

        self.search_input, self.status_combo, apply_btn = filter_bar(
            layout, search_placeholder="Search by name, license, phone, or email…",
            status_options=DRIVER_STATUSES,
        )
        apply_btn.clicked.connect(self.refresh_data)
        self.search_input.returnPressed.connect(self.refresh_data)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Name", "Phone", "Email", "License",
             "Assigned Truck", "Status", "Actions"]
        )
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        for col, w in [(0, 50), (4, 120), (5, 140), (6, 110), (7, 200)]:
            h.setSectionResizeMode(col, QHeaderView.Fixed)
            self.table.setColumnWidth(col, w)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(42)
        layout.addWidget(self.table)

    # ------------------------------------------------------------------
    def refresh_data(self):
        if self.current_user is None:
            return
        try:
            drivers = self.service.list_drivers(
                search=self.search_input.text(),
                status=self.status_combo.currentData() or None,
            )
        except Exception as exc:
            show_toast(self, f"Failed to load drivers: {exc}", "error")
            return

        self.table.setRowCount(0)
        for d in drivers:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(d.id)))
            self.table.setItem(row, 1, QTableWidgetItem(d.name))
            self.table.setItem(row, 2, QTableWidgetItem(d.phone or "—"))
            self.table.setItem(row, 3, QTableWidgetItem(d.email or "—"))
            self.table.setItem(row, 4, QTableWidgetItem(d.license_number))
            truck_label = (f"{d.truck.truck_code}" if getattr(d, "truck", None)
                           else "—")
            self.table.setItem(row, 5, QTableWidgetItem(truck_label))
            self.table.setItem(row, 6, status_item(d.status))
            self.table.setCellWidget(row, 7, self._row_actions(d))

    def _row_actions(self, driver) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(4, 4, 4, 4)
        h.setSpacing(6)
        h.setAlignment(Qt.AlignCenter)

        edit = secondary_button("Edit")
        edit.setEnabled(can(self.current_user, "driver.edit"))
        edit.clicked.connect(lambda _, d=driver: self._edit(d))
        h.addWidget(edit)

        delete = danger_button("Deactivate")
        delete.setEnabled(can(self.current_user, "driver.delete"))
        delete.clicked.connect(lambda _, did=driver.id, name=driver.name:
                               self._delete(did, name))
        h.addWidget(delete)
        return w

    # ------------------------------------------------------------------
    def _add(self):
        if not can(self.current_user, "driver.create"):
            show_toast(self, "Permission denied.", "error")
            return
        trucks = self.truck_service.list_trucks()
        dialog = DriverDialog(trucks=trucks, parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return
        try:
            self.service.create(self.current_user, dialog.get_data())
            show_toast(self, "Driver added.", "success")
            self.refresh_data()
        except Exception as exc:
            show_toast(self, str(exc), "error")

    def _edit(self, driver):
        trucks = self.truck_service.list_trucks()
        dialog = DriverDialog(driver=driver, trucks=trucks, parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return
        try:
            self.service.update(self.current_user, driver.id, dialog.get_data())
            show_toast(self, "Driver updated.", "success")
            self.refresh_data()
        except Exception as exc:
            show_toast(self, str(exc), "error")

    def _delete(self, driver_id: int, name: str):
        confirm = QMessageBox.question(
            self, "Deactivate Driver",
            f"Deactivate driver '{name}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self.service.soft_delete(self.current_user, driver_id)
            show_toast(self, "Driver deactivated.", "success")
            self.refresh_data()
        except Exception as exc:
            show_toast(self, str(exc), "error")
