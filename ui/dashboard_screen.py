from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
    QPushButton, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer

from backend.data_provider import DataProvider
from ui.widgets.stat_card import StatCard
from ui.widgets.chart_widget import ChartWidget


# Ordered fill-level mapping with semantic colors (empty → overflowing).
FILL_LEVEL_ORDER = ["empty", "half", "almost_full", "full", "overflowing"]
FILL_LEVEL_COLORS = {
    "empty":       "#52796A",
    "half":        "#BAC5AC",
    "almost_full": "#FFC107",
    "full":        "#E57373",
    "overflowing": "#B71C1C",
}


def _pretty_level(level: str) -> str:
    return level.replace("_", " ").title()


class DashboardScreen(QWidget):
    """Main dashboard with KPI cards, fill-level distribution (donut + legend),
    daily/trend charts, and a verification breakdown.

    All numbers come from the database — no synthetic fallbacks.
    """

    REFRESH_INTERVAL_MS = 15000  # 15 seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = DataProvider()
        self._legend_rows = []  # widgets currently inserted into the fill-level legend
        self._build_ui()
        self._setup_auto_refresh()
        self.refresh_data()

    # ---------------- UI construction ----------------

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
        layout.addWidget(self._build_fill_level_panel())
        layout.addLayout(self._build_middle_row())
        layout.addWidget(self._build_trend_panel())

        # Empty state shown only when the DB has no detections at all
        self.empty_state = self._build_empty_state()
        layout.addWidget(self.empty_state)

        layout.addStretch()

        scroll.setWidget(content)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _build_header(self):
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        header = QLabel("Dashboard")
        header.setStyleSheet("font-size: 20pt; font-weight: bold; color: #E5E5E5;")

        self.subtitle = QLabel("Overview of waste management operations")
        self.subtitle.setStyleSheet("color: #BFC5C9; font-size: 11pt;")

        title_col.addWidget(header)
        title_col.addWidget(self.subtitle)

        header_row.addLayout(title_col)
        header_row.addStretch()

        self.last_updated_label = QLabel("Last updated: —")
        self.last_updated_label.setStyleSheet("color: #8A9095; font-size: 10pt;")
        header_row.addWidget(self.last_updated_label)

        self.refresh_btn = QPushButton("↻  Refresh")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setFixedHeight(34)
        self.refresh_btn.setStyleSheet(
            "background-color: #2A2F33; color: #E5E5E5; border: 1px solid #3A3F44; "
            "border-radius: 6px; padding: 4px 14px; font-size: 10pt; min-height: 0px;"
        )
        self.refresh_btn.clicked.connect(self.refresh_data)
        header_row.addWidget(self.refresh_btn)

        return header_row

    def _build_kpi_row(self):
        row = QHBoxLayout()
        row.setSpacing(16)

        self.card_total = StatCard(
            "Total Detections", "0", "All time", "#52796A", "\U0001f4e6"
        )
        self.card_today = StatCard(
            "Today's Detections", "0", "Since midnight", "#FFC107", "\U0001f4c5"
        )
        self.card_pending = StatCard(
            "Pending Verifications", "0", "Awaiting review", "#64B5F6", "✅"
        )
        self.card_alerts = StatCard(
            "Active Alerts", "0", "Unacknowledged", "#E57373", "\U0001f514"
        )

        row.addWidget(self.card_total)
        row.addWidget(self.card_today)
        row.addWidget(self.card_pending)
        row.addWidget(self.card_alerts)
        return row

    # --- Fill-Level Distribution: donut + legend, full panel width ---------

    def _build_fill_level_panel(self):
        frame, frame_layout = self._make_panel("Bin Fill-Level Distribution")

        body_row = QHBoxLayout()
        body_row.setSpacing(28)
        body_row.setContentsMargins(8, 4, 8, 8)

        # Donut chart on the left
        self.fill_chart = ChartWidget(parent=self, width=4.6, height=4.6)
        self.fill_chart.setMinimumSize(320, 300)
        self.fill_chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        body_row.addWidget(self.fill_chart, 3)

        # Legend on the right (Qt widgets — readable, themeable, no matplotlib clutter)
        self.fill_legend_container = QFrame()
        self.fill_legend_container.setStyleSheet("background: transparent;")
        self.fill_legend_layout = QVBoxLayout(self.fill_legend_container)
        self.fill_legend_layout.setContentsMargins(0, 8, 0, 8)
        self.fill_legend_layout.setSpacing(12)
        self.fill_legend_layout.addStretch()
        body_row.addWidget(self.fill_legend_container, 2)

        frame_layout.addLayout(body_row)

        self.fill_empty_label = QLabel(
            "No detections yet — run a detection to see the fill-level breakdown."
        )
        self.fill_empty_label.setStyleSheet("color: #8A9095; font-size: 11pt;")
        self.fill_empty_label.setAlignment(Qt.AlignCenter)
        self.fill_empty_label.setWordWrap(True)
        self.fill_empty_label.hide()
        frame_layout.addWidget(self.fill_empty_label)

        self._fill_body_row = body_row
        return frame

    def _make_legend_row(self, color: str, name: str, count: int, pct: float):
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(12)

        # Color swatch (rounded square)
        swatch = QLabel()
        swatch.setFixedSize(14, 14)
        swatch.setStyleSheet(
            f"background-color: {color}; border-radius: 4px; border: none;"
        )
        h.addWidget(swatch)

        # Level name
        name_label = QLabel(name)
        name_label.setStyleSheet(
            "color: #E5E5E5; font-size: 12pt; font-weight: 500; background: transparent;"
        )
        h.addWidget(name_label)

        h.addStretch()

        # Count + percentage, right-aligned
        count_label = QLabel(f"{count:,}")
        count_label.setStyleSheet(
            "color: #E5E5E5; font-size: 13pt; font-weight: bold; background: transparent;"
        )
        count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h.addWidget(count_label)

        pct_label = QLabel(f"({pct:.0f}%)")
        pct_label.setFixedWidth(56)
        pct_label.setStyleSheet(
            "color: #BFC5C9; font-size: 11pt; background: transparent;"
        )
        pct_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h.addWidget(pct_label)

        return row

    def _clear_fill_legend(self):
        for widget in self._legend_rows:
            self.fill_legend_layout.removeWidget(widget)
            widget.deleteLater()
        self._legend_rows = []

    # --- Middle row: daily bar + verification breakdown --------------------

    def _build_middle_row(self):
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(self._build_daily_panel(), 2)
        row.addWidget(self._build_status_panel(), 1)
        return row

    def _build_daily_panel(self):
        frame, frame_layout = self._make_panel("Daily Detections (Last 7 Days)")
        self.bar_chart = ChartWidget(parent=self, width=5, height=3.5)
        self.bar_chart.setMinimumHeight(260)
        frame_layout.addWidget(self.bar_chart)
        self.bar_empty_label = QLabel("No data for the last 7 days.")
        self.bar_empty_label.setStyleSheet("color: #8A9095; font-size: 11pt;")
        self.bar_empty_label.setAlignment(Qt.AlignCenter)
        self.bar_empty_label.hide()
        frame_layout.addWidget(self.bar_empty_label)
        return frame

    def _build_status_panel(self):
        frame, frame_layout = self._make_panel("Verification Breakdown")

        self.status_rows = {}
        for key, label, color in [
            ("pending",  "Pending",  "#FFC107"),
            ("verified", "Verified", "#4CAF50"),
            ("rejected", "Rejected", "#E57373"),
        ]:
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 14pt;")
            name = QLabel(label)
            name.setStyleSheet("color: #E5E5E5; font-size: 12pt;")
            count_label = QLabel("0")
            count_label.setStyleSheet(
                f"color: {color}; font-size: 14pt; font-weight: bold;"
            )
            count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(dot)
            row.addWidget(name)
            row.addStretch()
            row.addWidget(count_label)
            frame_layout.addLayout(row)
            self.status_rows[key] = count_label

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #2E3338;")
        frame_layout.addSpacing(8)
        frame_layout.addWidget(sep)
        frame_layout.addSpacing(8)

        self.avg_conf_label = QLabel("Avg Confidence: —")
        self.avg_conf_label.setStyleSheet("color: #BFC5C9; font-size: 11pt;")
        frame_layout.addWidget(self.avg_conf_label)

        self.last_detection_label = QLabel("Last Detection: —")
        self.last_detection_label.setStyleSheet("color: #BFC5C9; font-size: 11pt;")
        frame_layout.addWidget(self.last_detection_label)

        self.week_count_label = QLabel("This Week: 0 detection(s)")
        self.week_count_label.setStyleSheet("color: #BFC5C9; font-size: 11pt;")
        frame_layout.addWidget(self.week_count_label)

        frame_layout.addStretch()
        return frame

    # --- Trend (full width) ------------------------------------------------

    def _build_trend_panel(self):
        frame, frame_layout = self._make_panel("Detection Trend (Last 30 Days)")
        self.trend_chart = ChartWidget(parent=self, width=10, height=3)
        self.trend_chart.setMinimumHeight(220)
        frame_layout.addWidget(self.trend_chart)
        self.trend_empty_label = QLabel("No data for the last 30 days.")
        self.trend_empty_label.setStyleSheet("color: #8A9095; font-size: 11pt;")
        self.trend_empty_label.setAlignment(Qt.AlignCenter)
        self.trend_empty_label.hide()
        frame_layout.addWidget(self.trend_empty_label)
        return frame

    def _build_empty_state(self):
        frame = QFrame()
        frame.setStyleSheet(
            "background-color: #222629; border: 1px dashed #3A3F44; border-radius: 12px;"
        )
        v = QVBoxLayout(frame)
        v.setContentsMargins(28, 24, 28, 24)
        v.setAlignment(Qt.AlignCenter)

        icon = QLabel("\U0001f4ca")
        icon.setStyleSheet("font-size: 28pt; background: transparent;")
        icon.setAlignment(Qt.AlignCenter)

        msg = QLabel(
            "No detections recorded yet. Head to the Detection screen and run "
            "your first detection to populate the dashboard."
        )
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet("color: #BFC5C9; font-size: 11pt; background: transparent;")

        v.addWidget(icon)
        v.addWidget(msg)
        frame.hide()
        return frame

    @staticmethod
    def _make_panel(title: str):
        frame = QFrame()
        frame.setProperty("class", "chart-frame")
        frame.setStyleSheet(
            "QFrame[class=\"chart-frame\"] { background-color: #222629; "
            "border: 1px solid #2E3338; border-radius: 12px; }"
        )
        v = QVBoxLayout(frame)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(8)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 13pt; font-weight: bold; color: #E5E5E5;")
        v.addWidget(title_label)
        return frame, v

    # ---------------- Refresh / data binding ----------------

    def _setup_auto_refresh(self):
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh_data)
        self._refresh_timer.start(self.REFRESH_INTERVAL_MS)

    def refresh_data(self):
        stats = self.data.get_summary_stats()

        # KPI cards
        self.card_total.update_value(self._fmt_int(stats["total_detections"]))
        self.card_today.update_value(self._fmt_int(stats["today_detections"]))
        self.card_pending.update_value(self._fmt_int(stats["pending_verifications"]))

        alerts = stats["active_alerts"]
        self.card_alerts.update_value(self._fmt_int(alerts))
        self.card_alerts.set_alert_mode(alerts > 0)

        # Status panel footer
        avg_conf = stats["avg_confidence"]
        self.avg_conf_label.setText(
            f"Avg Confidence: {avg_conf:.0%}" if avg_conf > 0 else "Avg Confidence: —"
        )
        last_dt = stats["last_detection_at"]
        self.last_detection_label.setText(
            f"Last Detection: {last_dt.strftime('%Y-%m-%d %H:%M')}"
            if last_dt else "Last Detection: —"
        )
        self.week_count_label.setText(
            f"This Week: {self._fmt_int(stats['week_detections'])} detection(s)"
        )

        # Charts
        self._refresh_fill_level_chart()
        self._refresh_daily_chart()
        self._refresh_trend_chart()
        self._refresh_status_breakdown()

        # Empty state
        self.empty_state.setVisible(stats["total_detections"] == 0)

        self.last_updated_label.setText(
            f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
        )

    def _refresh_fill_level_chart(self):
        dist = self.data.get_fill_level_distribution() or {}

        # Build ordered (level, count) list — known levels first, then any extras.
        ordered = [(lvl, dist[lvl]) for lvl in FILL_LEVEL_ORDER
                   if dist.get(lvl, 0) > 0]
        for lvl, count in dist.items():
            if lvl not in FILL_LEVEL_ORDER and count > 0:
                ordered.append((lvl, count))

        # Always rebuild the legend to reflect current data
        self._clear_fill_legend()

        total = sum(count for _, count in ordered)
        if total == 0:
            self.fill_chart.clear_chart()
            self.fill_chart.hide()
            self.fill_empty_label.show()
            return

        self.fill_empty_label.hide()
        self.fill_chart.show()

        labels = [_pretty_level(lvl) for lvl, _ in ordered]
        values = [count for _, count in ordered]
        color_map = {
            _pretty_level(lvl): FILL_LEVEL_COLORS.get(lvl, "#64B5F6")
            for lvl, _ in ordered
        }

        self.fill_chart.plot_donut(
            labels, values,
            title="",
            center_text=self._fmt_int(total),
            center_subtext="Total Bins",
            color_map=color_map,
            min_label_pct=8.0,
        )

        # Build the side legend rows (insert above the trailing stretch)
        insert_at = max(0, self.fill_legend_layout.count() - 1)
        for lvl, count in ordered:
            pct = (count / total) * 100.0
            color = FILL_LEVEL_COLORS.get(lvl, "#64B5F6")
            row = self._make_legend_row(color, _pretty_level(lvl), count, pct)
            self.fill_legend_layout.insertWidget(insert_at, row)
            self._legend_rows.append(row)
            insert_at += 1

    def _refresh_daily_chart(self):
        dates, counts = self.data.get_daily_detections(7)
        if not dates or sum(counts) == 0:
            self.bar_chart.clear_chart()
            self.bar_chart.hide()
            self.bar_empty_label.show()
            return
        self.bar_empty_label.hide()
        self.bar_chart.show()
        self.bar_chart.plot_bar(dates, counts, "")

    def _refresh_trend_chart(self):
        dates, counts = self.data.get_trend_data(30)
        if not dates or sum(counts) == 0:
            self.trend_chart.clear_chart()
            self.trend_chart.hide()
            self.trend_empty_label.show()
            return
        self.trend_empty_label.hide()
        self.trend_chart.show()
        self.trend_chart.plot_line(dates, counts, "", "Date", "Detections")

    def _refresh_status_breakdown(self):
        breakdown = self.data.get_status_breakdown()
        for key, label_widget in self.status_rows.items():
            label_widget.setText(self._fmt_int(breakdown.get(key, 0)))

    @staticmethod
    def _fmt_int(value) -> str:
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return "0"
