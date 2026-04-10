
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QScrollArea,
    QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer

from backend.data_provider import DataProvider
from ui.widgets.stat_card import StatCard
from ui.widgets.chart_widget import ChartWidget
from ui.widgets.toast import show_toast


class DashboardScreen(QWidget):
    """Main dashboard with stat cards, charts, and auto-refresh."""

    REFRESH_INTERVAL_MS = 5000  # 5 seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = DataProvider()
        self._build_ui()
        self._setup_auto_refresh()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Page header
        header = QLabel("Dashboard")
        header.setProperty("class", "screen-title")
        header.setStyleSheet("font-size: 20pt; font-weight: bold; color: #E5E5E5;")
        layout.addWidget(header)

        subtitle = QLabel("Overview of waste management operations")
        subtitle.setStyleSheet("color: #BFC5C9; font-size: 11pt; margin-bottom: 8px;")
        layout.addWidget(subtitle)

        # Stat cards row — with icons
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.card_total = StatCard(
            "Total Detections", "0", "All time", "#52796A", "\U0001f4e6"  # 📦
        )
        self.card_today = StatCard(
            "Today's Detections", "0", "Since midnight", "#FFC107", "\U0001f4c5"  # 📅
        )
        self.card_category = StatCard(
            "Top Category", "N/A", "Most detected", "#64B5F6", "\U0001f3f7"  # 🏷
        )
        self.card_alerts = StatCard(
            "Active Alerts", "0", "Unacknowledged", "#E57373", "\U0001f514"  # 🔔
        )

        cards_layout.addWidget(self.card_total)
        cards_layout.addWidget(self.card_today)
        cards_layout.addWidget(self.card_category)
        cards_layout.addWidget(self.card_alerts)
        layout.addLayout(cards_layout)

        # Charts row (pie + bar)
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(16)

        # Category distribution pie chart
        pie_frame = QFrame()
        pie_frame.setProperty("class", "chart-frame")
        pie_layout = QVBoxLayout(pie_frame)
        pie_layout.setContentsMargins(18, 18, 18, 14)

        pie_title = QLabel("Waste Category Distribution")
        pie_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #E5E5E5;")
        self.pie_chart = ChartWidget(parent=self, width=5, height=3.5)

        pie_layout.addWidget(pie_title)
        pie_layout.addWidget(self.pie_chart)

        # Daily detections bar chart
        bar_frame = QFrame()
        bar_frame.setProperty("class", "chart-frame")
        bar_layout = QVBoxLayout(bar_frame)
        bar_layout.setContentsMargins(18, 18, 18, 14)

        bar_title = QLabel("Daily Detections (Last 7 Days)")
        bar_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #E5E5E5;")
        self.bar_chart = ChartWidget(parent=self, width=5, height=3.5)

        bar_layout.addWidget(bar_title)
        bar_layout.addWidget(self.bar_chart)

        charts_layout.addWidget(pie_frame)
        charts_layout.addWidget(bar_frame)
        layout.addLayout(charts_layout)

        # Full-width trend line chart
        trend_frame = QFrame()
        trend_frame.setProperty("class", "chart-frame")
        trend_layout = QVBoxLayout(trend_frame)
        trend_layout.setContentsMargins(18, 18, 18, 14)

        trend_title = QLabel("Detection Trend (Last 30 Days)")
        trend_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #E5E5E5;")
        self.trend_chart = ChartWidget(parent=self, width=10, height=3)

        trend_layout.addWidget(trend_title)
        trend_layout.addWidget(self.trend_chart)
        layout.addWidget(trend_frame)

        layout.addStretch()

        scroll.setWidget(content)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _setup_auto_refresh(self):
        """Set up a timer to refresh dashboard data periodically."""
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh_data)
        self._refresh_timer.start(self.REFRESH_INTERVAL_MS)

    def refresh_data(self):
        """Reload all dashboard data from the data provider."""
        # Summary stats
        stats = self.data.get_summary_stats()

        self.card_total.update_value(str(stats["total_detections"]))
        self.card_today.update_value(str(stats["today_detections"]))
        self.card_category.update_value(stats["top_category"])

        alert_count = stats["active_alerts"]
        self.card_alerts.update_value(str(alert_count))
        self.card_alerts.set_alert_mode(alert_count > 0)

        # Pie chart
        cat_dist = self.data.get_category_distribution()
        if cat_dist:
            self.pie_chart.plot_pie(
                list(cat_dist.keys()), list(cat_dist.values()), ""
            )
        else:
            self.pie_chart.clear_chart()

        # Bar chart (7 days)
        dates, counts = self.data.get_daily_detections(7)
        if dates:
            self.bar_chart.plot_bar(dates, counts, "")
        else:
            self.bar_chart.clear_chart()

        # Trend line (30 days)
        t_dates, t_counts = self.data.get_trend_data(30)
        if t_dates:
            self.trend_chart.plot_line(t_dates, t_counts, "", "Date", "Detections")
        else:
            self.trend_chart.clear_chart()
