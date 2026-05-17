"""Trucks CRUD screen."""

from datetime import date

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox,
    QDateEdit, QTextEdit, QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import Qt, QDate

from core.fleet.truck_service import TruckService
from core.fleet.constants import TRUCK_STATUSES, FUEL_TYPES, pretty
from core.fleet.fleet_permissions import can
from ui.widgets.toast import show_toast
from ui.fleet._common import (
    build_header, primary_button, secondary_button, danger_button,
    filter_bar, status_item
)


class TruckDialog(QDialog):
    def __init__(self, truck=None, parent=None):
        super().__init__(parent)
        self.truck = truck
        self.setWindowTitle("Edit Truck" if truck else "Add Truck")
        self.setMinimumWidth(460)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        self.code_input = QLineEdit(self.truck.truck_code if self.truck else "")
        self.code_input.setPlaceholderText("e.g. TRK-001")
        layout.addRow("Truck Code:", self.code_input)

        self.plate_input = QLineEdit(self.truck.plate_number if self.truck else "")
        self.plate_input.setPlaceholderText("e.g. DH-1234")
        layout.addRow("Plate Number:", self.plate_input)

        self.capacity_input = QDoubleSpinBox()
        self.capacity_input.setSuffix(" kg")
        self.capacity_input.setRange(0.0, 100000.0)
        self.capacity_input.setDecimals(1)
        self.capacity_input.setValue(float(self.truck.capacity) if self.truck else 0.0)
        layout.addRow("Capacity:", self.capacity_input)

        self.fuel_combo = QComboBox()
        for ft in FUEL_TYPES:
            self.fuel_combo.addItem(pretty(ft), ft)
        if self.truck:
            i = self.fuel_combo.findData(self.truck.fuel_type)
            if i >= 0:
                self.fuel_combo.setCurrentIndex(i)
        layout.addRow("Fuel Type:", self.fuel_combo)

        self.status_combo = QComboBox()
        for s in TRUCK_STATUSES:
            self.status_combo.addItem(pretty(s), s)
        if self.truck:
            i = self.status_combo.findData(self.truck.status)
            if i >= 0:
                self.status_combo.setCurrentIndex(i)
        layout.addRow("Status:", self.status_combo)

        self.zone_input = QLineEdit(self.truck.assigned_zone if self.truck else "")
        self.zone_input.setPlaceholderText("e.g. Zone A — Downtown")
        layout.addRow("Assigned Zone:", self.zone_input)

        self.purchase_input = QDateEdit()
        self.purchase_input.setCalendarPopup(True)
        self.purchase_input.setDisplayFormat("yyyy-MM-dd")
        if self.truck and self.truck.purchase_date:
            d = self.truck.purchase_date
            self.purchase_input.setDate(QDate(d.year, d.month, d.day))
        else:
            self.purchase_input.setDate(QDate.currentDate())
        layout.addRow("Purchase Date:", self.purchase_input)

        self.notes_input = QTextEdit(self.truck.notes if self.truck else "")
        self.notes_input.setFixedHeight(70)
        layout.addRow("Notes:", self.notes_input)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_data(self) -> dict:
        qd = self.purchase_input.date()
        return {
            "truck_code": self.code_input.text(),
            "plate_number": self.plate_input.text(),
            "capacity": self.capacity_input.value(),
            "fuel_type": self.fuel_combo.currentData(),
            "status": self.status_combo.currentData(),
            "assigned_zone": self.zone_input.text(),
            "purchase_date": date(qd.year(), qd.month(), qd.day()),
            "notes": self.notes_input.toPlainText(),
        }


class TrucksScreen(QWidget):
    """Manage trucks — list, search, create, edit, soft-delete."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_user = None
        self.service = TruckService()
        self._build_ui()

    def set_user(self, user):
        self.current_user = user
        self._sync_permissions()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_row = build_header("Truck Management",
                                  "Fleet inventory & status")
        self.add_btn = primary_button("➕  Add Truck")
        self.add_btn.clicked.connect(self._add)
        header_row.addWidget(self.add_btn)
        layout.addLayout(header_row)

        self.search_input, self.status_combo, apply_btn = filter_bar(
            layout, search_placeholder="Search by code, plate, or zone…",
            status_options=TRUCK_STATUSES,
        )
        apply_btn.clicked.connect(self.refresh_data)
        self.search_input.returnPressed.connect(self.refresh_data)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Code", "Plate", "Capacity", "Fuel",
             "Zone", "Status", "Actions"]
        )
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        for col, w in [(0, 50), (1, 100), (2, 110), (3, 90), (4, 90), (6, 130), (7, 200)]:
            h.setSectionResizeMode(col, QHeaderView.Fixed)
            self.table.setColumnWidth(col, w)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(42)
        layout.addWidget(self.table)

    def _sync_permissions(self):
        u = self.current_user
        self.add_btn.setEnabled(can(u, "truck.create"))

    # ------------------------------------------------------------------
    def refresh_data(self):
        if self.current_user is None:
            return
        try:
            search = self.search_input.text()
            status = self.status_combo.currentData() or None
            trucks = self.service.list_trucks(search=search, status=status)
        except Exception as exc:
            show_toast(self, f"Failed to load trucks: {exc}", "error")
            return

        self.table.setRowCount(0)
        for truck in trucks:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(truck.id)))
            self.table.setItem(row, 1, QTableWidgetItem(truck.truck_code))
            self.table.setItem(row, 2, QTableWidgetItem(truck.plate_number))
            self.table.setItem(row, 3, QTableWidgetItem(f"{truck.capacity:.0f} kg"))
            self.table.setItem(row, 4, QTableWidgetItem(pretty(truck.fuel_type)))
            self.table.setItem(row, 5, QTableWidgetItem(truck.assigned_zone or "—"))
            self.table.setItem(row, 6, status_item(truck.status))
            self.table.setCellWidget(row, 7, self._row_actions(truck))

    def _row_actions(self, truck) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(4, 4, 4, 4)
        h.setSpacing(6)
        h.setAlignment(Qt.AlignCenter)

        edit = secondary_button("Edit")
        edit.setEnabled(can(self.current_user, "truck.edit"))
        edit.clicked.connect(lambda _, t=truck: self._edit(t))
        h.addWidget(edit)

        delete = danger_button("Deactivate")
        delete.setEnabled(can(self.current_user, "truck.delete"))
        delete.clicked.connect(lambda _, tid=truck.id, code=truck.truck_code:
                               self._delete(tid, code))
        h.addWidget(delete)
        return w

    # ------------------------------------------------------------------
    def _add(self):
        if not can(self.current_user, "truck.create"):
            show_toast(self, "Permission denied.", "error")
            return
        dialog = TruckDialog(parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return
        try:
            self.service.create(self.current_user, dialog.get_data())
            show_toast(self, "Truck added.", "success")
            self.refresh_data()
        except Exception as exc:
            show_toast(self, str(exc), "error")

    def _edit(self, truck):
        dialog = TruckDialog(truck=truck, parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return
        try:
            self.service.update(self.current_user, truck.id, dialog.get_data())
            show_toast(self, "Truck updated.", "success")
            self.refresh_data()
        except Exception as exc:
            show_toast(self, str(exc), "error")

    def _delete(self, truck_id: int, code: str):
        confirm = QMessageBox.question(
            self, "Deactivate Truck",
            f"Deactivate truck '{code}'? It can be restored later.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self.service.soft_delete(self.current_user, truck_id)
            show_toast(self, "Truck deactivated.", "success")
            self.refresh_data()
        except Exception as exc:
            show_toast(self, str(exc), "error")
