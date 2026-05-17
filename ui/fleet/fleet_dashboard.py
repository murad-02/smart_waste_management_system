"""Fleet operations dashboard — KPIs + charts.

Mirrors the structure of ui.dashboard_screen.DashboardScreen so users
get a consistent experience moving between modules.
"""

from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
    QPushButton, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer

from ui.widgets.stat_card import StatCard
from ui.widgets.chart_widget import ChartWidget
from core.fleet.fleet_analytics import FleetAnalytics
from core.fleet.maintenance_service import MaintenanceService


class FleetDashboardScreen(QWidget):
    """KPI cards + utilisation / trip / maintenance charts."""

    REFRESH_INTERVAL_MS = 30_000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_user = None
        self.analytics = FleetAnalytics()
        self.maintenance = MaintenanceService()
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_data)
        self._timer.start(self.REFRESH_INTERVAL_MS)

    def set_user(self, user):
        self.current_user = user

    # ------------------------------------------------------------------
    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        layout.addLayout(self._build_header())
        layout.addLayout(self._build_kpi_row())
        layout.addLayout(self._build_chart_row())
        layout.addWidget(self._build_alerts_panel())
        layout.addStretch()

        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _build_header(self):
        row = QHBoxLayout()
        row.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("Fleet Dashboard")
        title.setStyleSheet("font-size: 20pt; font-weight: bold; color: #E5E5E5;")
        subtitle = QLabel("Operational overview — trucks, trips, maintenance")
        subtitle.setStyleSheet("color: #BFC5C9; font-size: 11pt;")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        row.addLayout(title_col)
        row.addStretch()

        self.last_updated_label = QLabel("Last updated: —")
        self.last_updated_label.setStyleSheet("color: #8A9095; font-size: 10pt;")
        row.addWidget(self.last_updated_label)

        refresh = QPushButton("↻  Refresh")
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.setFixedHeight(34)
        refresh.setStyleSheet(
            "background-color: #2A2F33; color: #E5E5E5; border: 1px solid #3A3F44; "
            "border-radius: 6px; padding: 4px 14px; font-size: 10pt; min-height: 0px;"
        )
        refresh.clicked.connect(self.refresh_data)
        row.addWidget(refresh)
        return row

    def _build_kpi_row(self):
        row = QHBoxLayout()
        row.setSpacing(16)
        self.card_total = StatCard("Total Trucks", "0", "Active fleet",
                                   "#52796A", "🚛")
        self.card_active = StatCard("On Route / Available", "0", "Operational",
                                    "#4CAF50", "✅")
        self.card_maint = StatCard("In Maintenance", "0", "Service bay",
                                   "#FFC107", "🔧")
        self.card_trips = StatCard("Trips Today", "0", "Scheduled + active",
                                   "#64B5F6", "📋")
        self.card_due = StatCard("Maintenance Due", "0", "Next 14 days",
                                 "#E57373", "🛎️")

        for card in (self.card_total, self.card_active, self.card_maint,
                     self.card_trips, self.card_due):
            row.addWidget(card)
        return row

    def _build_chart_row(self):
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(self._build_trips_panel(), 1)
        row.addWidget(self._build_utilisation_panel(), 1)
        row.addWidget(self._build_maint_panel(), 1)
        return row

    def _build_trips_panel(self):
        frame, body = self._panel("Trips per Day (Last 7 Days)")
        self.trips_chart = ChartWidget(parent=self, width=4, height=3)
        self.trips_chart.setMinimumHeight(220)
        body.addWidget(self.trips_chart)
        return frame

    def _build_utilisation_panel(self):
        frame, body = self._panel("Truck Utilisation (Last 30 Days)")
        self.util_chart = ChartWidget(parent=self, width=4, height=3)
        self.util_chart.setMinimumHeight(220)
        body.addWidget(self.util_chart)
        self.util_empty = QLabel("No utilisation data yet.")
        self.util_empty.setAlignment(Qt.AlignCenter)
        self.util_empty.setStyleSheet("color: #8A9095; font-size: 11pt;")
        self.util_empty.hide()
        body.addWidget(self.util_empty)
        return frame

    def _build_maint_panel(self):
        frame, body = self._panel("Maintenance Cost Trend (30 Days)")
        self.maint_chart = ChartWidget(parent=self, width=4, height=3)
        self.maint_chart.setMinimumHeight(220)
        body.addWidget(self.maint_chart)
        self.maint_summary_label = QLabel("Total: $0.00 over 0 records")
        self.maint_summary_label.setStyleSheet(
            "color: #BFC5C9; font-size: 11pt; padding-top: 4px;"
        )
        body.addWidget(self.maint_summary_label)
        return frame

    def _build_alerts_panel(self) -> QFrame:
        frame, body = self._panel("Upcoming Maintenance Alerts")
        self.alerts_label = QLabel("Loading…")
        self.alerts_label.setWordWrap(True)
        self.alerts_label.setStyleSheet("color: #E5E5E5; font-size: 11pt;")
        body.addWidget(self.alerts_label)
        return frame

    @staticmethod
    def _panel(title: str):
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background-color: #222629; border: 1px solid #2E3338;"
            " border-radius: 12px; }"
        )
        v = QVBoxLayout(frame)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(8)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 13pt; font-weight: bold; color: #E5E5E5;")
        v.addWidget(title_label)
        return frame, v

    # ------------------------------------------------------------------
    def refresh_data(self):
        try:
            summary = self.analytics.summary()
        except Exception:
            summary = {}

        self.card_total.update_value(str(summary.get("trucks_total", 0)))
        self.card_active.update_value(str(summary.get("trucks_active", 0)))
        self.card_maint.update_value(str(summary.get("trucks_maintenance", 0)))
        self.card_trips.update_value(str(summary.get("trips_today", 0)))
        self.card_due.update_value(str(summary.get("maintenance_due", 0)))
        self.card_due.set_alert_mode(summary.get("maintenance_due", 0) > 0)

        # Trips/day bar chart
        try:
            labels, counts = self.analytics.trips_per_day(7)
            if sum(counts) > 0:
                self.trips_chart.plot_bar(labels, counts, "")
            else:
                self.trips_chart.clear_chart()
        except Exception:
            self.trips_chart.clear_chart()

        # Utilisation bar chart
        try:
            util = self.analytics.truck_utilization(30)
            util = [u for u in util if u["utilization_pct"] > 0][:10]
            if util:
                self.util_empty.hide()
                self.util_chart.show()
                self.util_chart.plot_bar(
                    [u["truck_code"] for u in util],
                    [u["utilization_pct"] for u in util],
                    "",
                )
            else:
                self.util_chart.clear_chart()
                self.util_chart.hide()
                self.util_empty.show()
        except Exception:
            self.util_chart.clear_chart()

        # Maintenance trend
        try:
            labels, costs = self.analytics.maintenance_trend(30)
            if sum(costs) > 0:
                self.maint_chart.plot_line(labels, costs, "", "Date", "Cost ($)")
            else:
                self.maint_chart.clear_chart()
            summary_cost = self.analytics.maintenance_cost_summary(90)
            self.maint_summary_label.setText(
                f"Last 90 days: ${summary_cost['total_cost']:.2f} over "
                f"{summary_cost['records']} records "
                f"(avg ${summary_cost['avg_cost']:.2f})"
            )
        except Exception:
            self.maint_chart.clear_chart()

        # Alerts panel
        try:
            due_records = self.maintenance.list_due()
            if due_records:
                lines = [
                    f"• {r.truck.truck_code if r.truck else '—'}: "
                    f"{r.service_type.replace('_', ' ').title()} due "
                    f"{r.next_service_date}"
                    for r in due_records[:8]
                ]
                if len(due_records) > 8:
                    lines.append(f"…and {len(due_records) - 8} more")
                self.alerts_label.setText("\n".join(lines))
            else:
                self.alerts_label.setText("No maintenance due in the next 14 days.")
        except Exception as exc:
            self.alerts_label.setText(f"Failed to load alerts: {exc}")

        self.last_updated_label.setText(
            f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
        )
