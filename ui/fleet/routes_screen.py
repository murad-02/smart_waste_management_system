"""Routes CRUD screen."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox,
    QSpinBox, QTextEdit, QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import Qt

from core.fleet.route_service import RouteService
from core.fleet.constants import ROUTE_STATUSES, pretty
from core.fleet.fleet_permissions import can
from ui.widgets.toast import show_toast
from ui.fleet._common import (
    build_header, primary_button, secondary_button, danger_button,
    filter_bar, status_item
)


class RouteDialog(QDialog):
    def __init__(self, route=None, parent=None):
        super().__init__(parent)
        self.route = route
        self.setWindowTitle("Edit Route" if route else "Add Route")
        self.setMinimumWidth(460)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        self.name_input = QLineEdit(self.route.route_name if self.route else "")
        layout.addRow("Route Name:", self.name_input)

        self.zone_input = QLineEdit(self.route.zone if self.route else "")
        self.zone_input.setPlaceholderText("e.g. Zone B — North")
        layout.addRow("Zone:", self.zone_input)

        self.distance_input = QDoubleSpinBox()
        self.distance_input.setSuffix(" km")
        self.distance_input.setRange(0.0, 10000.0)
        self.distance_input.setDecimals(1)
        if self.route and self.route.estimated_distance is not None:
            self.distance_input.setValue(float(self.route.estimated_distance))
        layout.addRow("Estimated Distance:", self.distance_input)

        self.duration_input = QSpinBox()
        self.duration_input.setSuffix(" min")
        self.duration_input.setRange(0, 24 * 60)
        if self.route and self.route.estimated_duration is not None:
            self.duration_input.setValue(int(self.route.estimated_duration))
        layout.addRow("Estimated Duration:", self.duration_input)

        self.status_combo = QComboBox()
        for s in ROUTE_STATUSES:
            self.status_combo.addItem(pretty(s), s)
        if self.route:
            i = self.status_combo.findData(self.route.status)
            if i >= 0:
                self.status_combo.setCurrentIndex(i)
        layout.addRow("Status:", self.status_combo)

        self.notes_input = QTextEdit(self.route.notes if self.route else "")
        self.notes_input.setFixedHeight(70)
        layout.addRow("Notes:", self.notes_input)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_data(self) -> dict:
        return {
            "route_name": self.name_input.text(),
            "zone": self.zone_input.text(),
            "estimated_distance": self.distance_input.value() or None,
            "estimated_duration": self.duration_input.value() or None,
            "status": self.status_combo.currentData(),
            "notes": self.notes_input.toPlainText(),
        }


class RoutesScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_user = None
        self.service = RouteService()
        self._build_ui()

    def set_user(self, user):
        self.current_user = user
        self.add_btn.setEnabled(can(user, "route.create"))

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_row = build_header("Route Management",
                                  "Zones, distances & schedules")
        self.add_btn = primary_button("➕  Add Route")
        self.add_btn.clicked.connect(self._add)
        header_row.addWidget(self.add_btn)
        layout.addLayout(header_row)

        self.search_input, self.status_combo, apply_btn = filter_bar(
            layout, search_placeholder="Search by route name or zone…",
            status_options=ROUTE_STATUSES,
        )
        apply_btn.clicked.connect(self.refresh_data)
        self.search_input.returnPressed.connect(self.refresh_data)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Name", "Zone", "Distance", "Duration", "Status", "Actions"]
        )
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        for col, w in [(0, 50), (3, 100), (4, 100), (5, 110), (6, 200)]:
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
            routes = self.service.list_routes(
                search=self.search_input.text(),
                status=self.status_combo.currentData() or None,
            )
        except Exception as exc:
            show_toast(self, f"Failed to load routes: {exc}", "error")
            return

        self.table.setRowCount(0)
        for r in routes:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(r.id)))
            self.table.setItem(row, 1, QTableWidgetItem(r.route_name))
            self.table.setItem(row, 2, QTableWidgetItem(r.zone))
            dist_text = f"{r.estimated_distance:.1f} km" if r.estimated_distance else "—"
            self.table.setItem(row, 3, QTableWidgetItem(dist_text))
            dur_text = f"{r.estimated_duration} min" if r.estimated_duration else "—"
            self.table.setItem(row, 4, QTableWidgetItem(dur_text))
            self.table.setItem(row, 5, status_item(r.status))
            self.table.setCellWidget(row, 6, self._row_actions(r))

    def _row_actions(self, route) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(4, 4, 4, 4)
        h.setSpacing(6)
        h.setAlignment(Qt.AlignCenter)

        edit = secondary_button("Edit")
        edit.setEnabled(can(self.current_user, "route.edit"))
        edit.clicked.connect(lambda _, r=route: self._edit(r))
        h.addWidget(edit)

        delete = danger_button("Deactivate")
        delete.setEnabled(can(self.current_user, "route.delete"))
        delete.clicked.connect(lambda _, rid=route.id, name=route.route_name:
                               self._delete(rid, name))
        h.addWidget(delete)
        return w

    # ------------------------------------------------------------------
    def _add(self):
        if not can(self.current_user, "route.create"):
            show_toast(self, "Permission denied.", "error")
            return
        dialog = RouteDialog(parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return
        try:
            self.service.create(self.current_user, dialog.get_data())
            show_toast(self, "Route added.", "success")
            self.refresh_data()
        except Exception as exc:
            show_toast(self, str(exc), "error")

    def _edit(self, route):
        dialog = RouteDialog(route=route, parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return
        try:
            self.service.update(self.current_user, route.id, dialog.get_data())
            show_toast(self, "Route updated.", "success")
            self.refresh_data()
        except Exception as exc:
            show_toast(self, str(exc), "error")

    def _delete(self, route_id: int, name: str):
        confirm = QMessageBox.question(
            self, "Deactivate Route",
            f"Deactivate route '{name}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self.service.soft_delete(self.current_user, route_id)
            show_toast(self, "Route deactivated.", "success")
            self.refresh_data()
        except Exception as exc:
            show_toast(self, str(exc), "error")
