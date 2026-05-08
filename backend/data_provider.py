"""
Data provider layer that wraps AnalyticsEngine with a clean interface
for the dashboard. Returns only real data from the database — empty
results are surfaced honestly so the UI can render an empty state.
"""

from core.analytics_engine import AnalyticsEngine
from core.alert_manager import AlertManager


class DataProvider:
    """Provides dashboard data sourced from the database."""

    def __init__(self):
        self.analytics = AnalyticsEngine()
        self.alert_mgr = AlertManager()

    def get_summary_stats(self) -> dict:
        """Return KPI numbers for the four dashboard stat cards."""
        total = self.analytics.get_total_stats()
        today = self.analytics.get_today_stats()
        status = self.analytics.get_status_breakdown()

        return {
            "total_detections": total["total_detections"],
            "today_detections": today["total_today"],
            "week_detections": self.analytics.get_week_count(),
            "pending_verifications": status["pending"],
            "active_alerts": today["active_alerts"],
            "avg_confidence": self.analytics.get_avg_confidence(),
            "last_detection_at": self.analytics.get_last_detection_time(),
        }

    def get_fill_level_distribution(self) -> dict:
        """Return {fill_level: count} across all detections."""
        return self.analytics.get_fill_level_distribution()

    def get_status_breakdown(self) -> dict:
        """Return {pending, verified, rejected} counts."""
        return self.analytics.get_status_breakdown()

    def get_recent_detections(self, limit: int = 8) -> list:
        """Return the most recent detections."""
        return self.analytics.get_recent_detections(limit)

    def get_daily_detections(self, days: int = 7) -> tuple:
        """Return (date_labels, counts) for the bar chart. Empty on no data."""
        raw = self.analytics.get_daily_counts(days)
        if not raw:
            return [], []
        dates = [d["date"][-5:] for d in raw]
        counts = [d["count"] for d in raw]
        return dates, counts

    def get_trend_data(self, days: int = 30) -> tuple:
        """Return (date_labels, counts) for the trend line chart."""
        raw = self.analytics.get_trend_data(days)
        if not raw:
            return [], []
        dates = [d["date"][-5:] for d in raw]
        counts = [d["count"] for d in raw]
        return dates, counts
