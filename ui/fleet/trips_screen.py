"""Collection Trip CRUD + lifecycle screen."""

from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QComboBox, QDateTimeEdit,
    QDoubleSpinBox, QTextEdit, QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import Qt, QDateTime

from core.fleet.trip_service import TripService
from core.fleet.truck_service import TruckService
from core.fleet.driver_service import DriverService
from core.fleet.route_service import RouteService
from core.fleet.constants import TRIP_STATUSES, pretty
from core.fleet.fleet_permissions import can
from ui.widgets.toast import show_toast
from ui.fleet._common import (
    build_header, primary_button, secondary_button, danger_button,
    filter_bar, status_item
)


class TripDialog(QDialog):
    """Create/edit a trip — references fetched from service layer."""

    def __init__(self, trip=None, trucks=None, drivers=None, routes=None,
                 readonly_refs: bool = False, parent=None):
        super().__init__(parent)
        self.trip = trip
        self.trucks = trucks or []
        self.drivers = drivers or []
        self.routes = routes or []
        self.readonly_refs = readonly_refs
        self.setWindowTitle("Edit Trip" if trip else "Schedule Trip")
        self.setMinimumWidth(500)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        self.truck_combo = QComboBox()
        for t in self.trucks:
            self.truck_combo.addItem(f"{t.truck_code} ({t.plate_number})", t.id)
        if self.trip:
            i = self.truck_combo.findData(self.trip.truck_id)
            if i >= 0:
                self.truck_combo.setCurrentIndex(i)
        self.truck_combo.setDisabled(self.readonly_refs)
        layout.addRow("Truck:", self.truck_combo)

        self.driver_combo = QComboBox()
        for d in self.drivers:
            self.driver_combo.addItem(d.name, d.id)
        if self.trip:
            i = self.driver_combo.findData(self.trip.driver_id)
            if i >= 0:
                self.driver_combo.setCurrentIndex(i)
        self.driver_combo.setDisabled(self.readonly_refs)
        layout.addRow("Driver:", self.driver_combo)

        self.route_combo = QComboBox()
        for r in self.routes:
            self.route_combo.addItem(f"{r.route_name} — {r.zone}", r.id)
        if self.trip:
            i = self.route_combo.findData(self.trip.route_id)
            if i >= 0:
                self.route_combo.setCurrentIndex(i)
        self.route_combo.setDisabled(self.readonly_refs)
        layout.addRow("Route:", self.route_combo)

        self.start_input = QDateTimeEdit()
        self.start_input.setCalendarPopup(True)
        self.start_input.setDisplayFormat("yyyy-MM-dd HH:mm")
        if self.trip and self.trip.start_time:
            self.start_input.setDateTime(QDateTime(self.trip.start_time))
        else:
            self.start_input.setDateTime(QDateTime.currentDateTime())
        layout.addRow("Start Time:", self.start_input)

        self.end_input = QDateTimeEdit()
        self.end_input.setCalendarPopup(True)
        self.end_input.setDisplayFormat("yyyy-MM-dd HH:mm")
        if self.trip and self.trip.end_time:
            self.end_input.setDateTime(QDateTime(self.trip.end_time))
        else:
            self.end_input.setDateTime(QDateTime.currentDateTime())
        layout.addRow("End Time:", self.end_input)

        self.weight_input = QDoubleSpinBox()
        self.weight_input.setSuffix(" kg")
        self.weight_input.setRange(0.0, 100000.0)
        self.weight_input.setDecimals(1)
        if self.trip and self.trip.waste_weight:
            self.weight_input.setValue(float(self.trip.waste_weight))
        layout.addRow("Waste Weight:", self.weight_input)

        self.status_combo = QComboBox()
        for s in TRIP_STATUSES:
            self.status_combo.addItem(pretty(s), s)
        if self.trip:
            i = self.status_combo.findData(self.trip.trip_status)
            if i >= 0:
                self.status_combo.setCurrentIndex(i)
        layout.addRow("Status:", self.status_combo)

        self.notes_input = QTextEdit(self.trip.notes if self.trip else "")
        self.notes_input.setFixedHeight(70)
        layout.addRow("Notes:", self.notes_input)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_data(self) -> dict:
        return {
            "truck_id": self.truck_combo.currentData(),
            "driver_id": self.driver_combo.currentData(),
            "route_id": self.route_combo.currentData(),
            "start_time": self.start_input.dateTime().toPyDateTime(),
            "end_time": self.end_input.dateTime().toPyDateTime(),
            "waste_weight": self.weight_input.value(),
            "trip_status": self.status_combo.currentData(),
            "notes": self.notes_input.toPlainText(),
        }


class TripsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_user = None
        self.service = TripService()
        self.truck_service = TruckService()
        self.driver_service = DriverService()
        self.route_service = RouteService()
        self._build_ui()

    def set_user(self, user):
        self.current_user = user
        self.add_btn.setEnabled(can(user, "trip.create"))

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_row = build_header("Collection Trips",
                                  "Schedule & monitor operations")
        self.add_btn = primary_button("➕  Schedule Trip")
        self.add_btn.clicked.connect(self._add)
        header_row.addWidget(self.add_btn)
        layout.addLayout(header_row)

        self.search_input, self.status_combo, apply_btn = filter_bar(
            layout, search_placeholder="Search disabled — use status filter",
            status_options=TRIP_STATUSES,
        )
        self.search_input.setDisabled(True)
        apply_btn.clicked.connect(self.refresh_data)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Truck", "Driver", "Route", "Start", "End",
             "Weight (kg)", "Status", "Actions"]
        )
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        for col, w in [(0, 50), (6, 100), (7, 110), (8, 240)]:
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
            trips = self.service.list_trips(
                actor=self.current_user,
                status=self.status_combo.currentData() or None,
            )
        except Exception as exc:
            show_toast(self, f"Failed to load trips: {exc}", "error")
            return

        self.table.setRowCount(0)
        for t in trips:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(t.id)))
            self.table.setItem(row, 1, QTableWidgetItem(
                t.truck.truck_code if t.truck else "—"))
            self.table.setItem(row, 2, QTableWidgetItem(
                t.driver.name if t.driver else "—"))
            self.table.setItem(row, 3, QTableWidgetItem(
                t.route.route_name if t.route else "—"))
            self.table.setItem(row, 4, QTableWidgetItem(
                t.start_time.strftime("%Y-%m-%d %H:%M") if t.start_time else "—"))
            self.table.setItem(row, 5, QTableWidgetItem(
                t.end_time.strftime("%Y-%m-%d %H:%M") if t.end_time else "—"))
            self.table.setItem(row, 6, QTableWidgetItem(
                f"{t.waste_weight:.1f}" if t.waste_weight else "—"))
            self.table.setItem(row, 7, status_item(t.trip_status))
            self.table.setCellWidget(row, 8, self._row_actions(t))

    def _row_actions(self, trip) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(4, 4, 4, 4)
        h.setSpacing(6)
        h.setAlignment(Qt.AlignCenter)

        # Operators can only edit own trips; the service double-checks anyway.
        edit = secondary_button("Edit")
        is_own = trip.created_by == self.current_user.id
        edit.setEnabled(can(self.current_user, "trip.edit") or is_own)
        edit.clicked.connect(lambda _, t=trip: self._edit(t))
        h.addWidget(edit)

        # Quick lifecycle action — context-aware
        if trip.trip_status == "scheduled":
            start_btn = secondary_button("Start")
            start_btn.setEnabled(edit.isEnabled())
            start_btn.clicked.connect(
                lambda _, tid=trip.id: self._set_status(tid, "active"))
            h.addWidget(start_btn)
        elif trip.trip_status == "active":
            done_btn = secondary_button("Complete")
            done_btn.setEnabled(edit.isEnabled())
            done_btn.clicked.connect(
                lambda _, tid=trip.id: self._set_status(tid, "completed"))
            h.addWidget(done_btn)

        delete = danger_button("Delete")
        delete.setEnabled(can(self.current_user, "trip.delete"))
        delete.clicked.connect(lambda _, tid=trip.id: self._delete(tid))
        h.addWidget(delete)
        return w

    # ------------------------------------------------------------------
    def _load_references(self):
        return (self.truck_service.list_trucks(),
                self.driver_service.list_drivers(),
                self.route_service.list_routes())

    def _add(self):
        if not can(self.current_user, "trip.create"):
            show_toast(self, "Permission denied.", "error")
            return
        trucks, drivers, routes = self._load_references()
        if not (trucks and drivers and routes):
            show_toast(self, "Add at least one truck, driver, and route first.",
                       "warning")
            return
        dialog = TripDialog(trucks=trucks, drivers=drivers, routes=routes,
                            parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return
        try:
            self.service.create(self.current_user, dialog.get_data())
            show_toast(self, "Trip scheduled.", "success")
            self.refresh_data()
        except Exception as exc:
            show_toast(self, str(exc), "error")

    def _edit(self, trip):
        # Operators may not change refs — only progress status / weight / notes.
        is_full = can(self.current_user, "trip.edit")
        trucks, drivers, routes = self._load_references()
        dialog = TripDialog(trip=trip, trucks=trucks, drivers=drivers,
                            routes=routes, readonly_refs=not is_full,
                            parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return
        try:
            self.service.update(self.current_user, trip.id, dialog.get_data())
            show_toast(self, "Trip updated.", "success")
            self.refresh_data()
        except Exception as exc:
            show_toast(self, str(exc), "error")

    def _set_status(self, trip_id: int, status: str):
        try:
            self.service.set_status(self.current_user, trip_id, status)
            show_toast(self, f"Trip marked {pretty(status)}.", "success")
            self.refresh_data()
        except Exception as exc:
            show_toast(self, str(exc), "error")

    def _delete(self, trip_id: int):
        confirm = QMessageBox.question(
            self, "Delete Trip", f"Permanently delete trip #{trip_id}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self.service.delete(self.current_user, trip_id)
            show_toast(self, "Trip deleted.", "success")
            self.refresh_data()
        except Exception as exc:
            show_toast(self, str(exc), "error")
