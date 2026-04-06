from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QScrollArea,
    QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt

from core.analytics_engine import AnalyticsEngine
from ui.widgets.stat_card import StatCard
from ui.widgets.chart_widget import ChartWidget


class DashboardScreen(QWidget):
    """Main dashboard with stat cards and charts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.analytics = AnalyticsEngine()
        self._build_ui()

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
        header.setStyleSheet("font-size: 20pt; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(header)

        subtitle = QLabel("Overview of waste management operations")
        subtitle.setStyleSheet("color: #8888aa; font-size: 11pt;")
        layout.addWidget(subtitle)

        # Stat cards row
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.card_total = StatCard("Total Detections", "0", "All time", "#00b894")
        self.card_today = StatCard("Today's Detections", "0", "Since midnight", "#0984e3")
        self.card_category = StatCard("Top Category", "N/A", "Most detected", "#fdcb6e")
        self.card_alerts = StatCard("Active Alerts", "0", "Unacknowledged", "#d63031")

        cards_layout.addWidget(self.card_total)
        cards_layout.addWidget(self.card_today)
        cards_layout.addWidget(self.card_category)
        cards_layout.addWidget(self.card_alerts)
        layout.addLayout(cards_layout)

        # Charts row
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(16)

        # Category distribution pie chart
        pie_frame = QFrame()
        pie_frame.setStyleSheet(
            "background-color: #1a1a35; border: 1px solid #3a3a5a; border-radius: 12px;"
        )
        pie_layout = QVBoxLayout(pie_frame)
        pie_layout.setContentsMargins(12, 12, 12, 12)

        pie_title = QLabel("Waste Category Distribution")
        pie_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #e0e0e0;")
        self.pie_chart = ChartWidget(parent=self, width=5, height=3.5)

        pie_layout.addWidget(pie_title)
        pie_layout.addWidget(self.pie_chart)

        # Daily detections bar chart
        bar_frame = QFrame()
        bar_frame.setStyleSheet(
            "background-color: #1a1a35; border: 1px solid #3a3a5a; border-radius: 12px;"
        )
        bar_layout = QVBoxLayout(bar_frame)
        bar_layout.setContentsMargins(12, 12, 12, 12)

        bar_title = QLabel("Daily Detections (Last 7 Days)")
        bar_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #e0e0e0;")
        self.bar_chart = ChartWidget(parent=self, width=5, height=3.5)

        bar_layout.addWidget(bar_title)
        bar_layout.addWidget(self.bar_chart)

        charts_layout.addWidget(pie_frame)
        charts_layout.addWidget(bar_frame)
        layout.addLayout(charts_layout)

        # Trend line chart
        trend_frame = QFrame()
        trend_frame.setStyleSheet(
            "background-color: #1a1a35; border: 1px solid #3a3a5a; border-radius: 12px;"
        )
        trend_layout = QVBoxLayout(trend_frame)
        trend_layout.setContentsMargins(12, 12, 12, 12)

        trend_title = QLabel("Detection Trend (Last 30 Days)")
        trend_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #e0e0e0;")
        self.trend_chart = ChartWidget(parent=self, width=10, height=3)

        trend_layout.addWidget(trend_title)
        trend_layout.addWidget(self.trend_chart)
        layout.addWidget(trend_frame)

        layout.addStretch()

        scroll.setWidget(content)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def refresh_data(self):
        """Reload all dashboard data."""
        # Stats
        today_stats = self.analytics.get_today_stats()
        total_stats = self.analytics.get_total_stats()

        self.card_total.update_value(str(total_stats["total_detections"]))
        self.card_today.update_value(str(today_stats["total_today"]))
        self.card_category.update_value(today_stats["most_common_category"])
        self.card_alerts.update_value(str(today_stats["active_alerts"]))

        # Pie chart
        cat_dist = self.analytics.get_category_distribution()
        if cat_dist:
            self.pie_chart.plot_pie(
                list(cat_dist.keys()), list(cat_dist.values()),
                ""
            )
        else:
            self.pie_chart.clear_chart()

        # Bar chart (7 days)
        daily = self.analytics.get_daily_counts(7)
        if daily:
            dates = [d["date"][-5:] for d in daily]  # MM-DD
            counts = [d["count"] for d in daily]
            self.bar_chart.plot_bar(dates, counts, "")
        else:
            self.bar_chart.clear_chart()

        # Trend line (30 days)
        trend = self.analytics.get_trend_data(30)
        if trend:
            dates = [d["date"][-5:] for d in trend]
            counts = [d["count"] for d in trend]
            self.trend_chart.plot_line(dates, counts, "", "Date", "Detections")
        else:
            self.trend_chart.clear_chart()
