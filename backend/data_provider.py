"""
Data provider layer that wraps AnalyticsEngine and provides
a clean interface for the dashboard. Falls back to mock data
when the database has no records.
"""

import random
from datetime import datetime, timedelta

from core.analytics_engine import AnalyticsEngine


class DataProvider:
    """Provides dashboard data from real DB or simulated fallback."""

    def __init__(self):
        self.analytics = AnalyticsEngine()

    def get_summary_stats(self) -> dict:
        """Return summary stats for all four dashboard cards."""
        today = self.analytics.get_today_stats()
        total = self.analytics.get_total_stats()

        result = {
            "total_detections": total["total_detections"],
            "today_detections": today["total_today"],
            "top_category": today["most_common_category"],
            "active_alerts": today["active_alerts"],
        }

        # If DB is empty, provide simulated data so the dashboard isn't blank
        if result["total_detections"] == 0 and result["today_detections"] == 0:
            result = self._mock_summary()

        return result

    def get_category_distribution(self) -> dict:
        """Return {category: count} for pie chart."""
        data = self.analytics.get_category_distribution()
        if data:
            return data
        return self._mock_category_distribution()

    def get_daily_detections(self, days: int = 7) -> tuple:
        """Return (dates, counts) for bar chart."""
        raw = self.analytics.get_daily_counts(days)
        if raw and any(d["count"] > 0 for d in raw):
            dates = [d["date"][-5:] for d in raw]
            counts = [d["count"] for d in raw]
            return dates, counts
        return self._mock_daily_detections(days)

    def get_trend_data(self, days: int = 30) -> tuple:
        """Return (dates, counts) for line chart."""
        raw = self.analytics.get_trend_data(days)
        if raw and any(d["count"] > 0 for d in raw):
            dates = [d["date"][-5:] for d in raw]
            counts = [d["count"] for d in raw]
            return dates, counts
        return self._mock_trend_data(days)

    # ------ Mock data generators (used when DB is empty) ------

    @staticmethod
    def _mock_summary() -> dict:
        return {
            "total_detections": random.randint(1200, 1600),
            "today_detections": random.randint(15, 45),
            "top_category": random.choice(["Plastic", "Paper", "Organic"]),
            "active_alerts": random.randint(0, 5),
        }

    @staticmethod
    def _mock_category_distribution() -> dict:
        return {
            "Plastic": random.randint(300, 500),
            "Paper": random.randint(200, 350),
            "Organic": random.randint(150, 280),
            "Metal": random.randint(80, 150),
            "Glass": random.randint(60, 120),
            "Hazardous": random.randint(20, 60),
            "E-Waste": random.randint(10, 40),
        }

    @staticmethod
    def _mock_daily_detections(days: int = 7) -> tuple:
        today = datetime.utcnow().date()
        dates = [(today - timedelta(days=i)).strftime("%m-%d") for i in range(days - 1, -1, -1)]
        counts = [random.randint(10, 50) for _ in range(days)]
        return dates, counts

    @staticmethod
    def _mock_trend_data(days: int = 30) -> tuple:
        today = datetime.utcnow().date()
        dates = [(today - timedelta(days=i)).strftime("%m-%d") for i in range(days - 1, -1, -1)]
        base = 25
        counts = []
        for _ in range(days):
            base += random.randint(-3, 5)
            base = max(5, base)
            counts.append(base)
        return dates, counts
