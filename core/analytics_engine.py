from datetime import datetime, timedelta

from sqlalchemy import func

from database.db_setup import Session
from database.models import Detection, Alert, User


class AnalyticsEngine:
    """Queries the database and aggregates statistics for dashboard and reports."""

    def get_today_stats(self) -> dict:
        """Return total detections today, most common category, active alerts count."""
        session = Session()
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            total_today = session.query(func.count(Detection.id)).filter(
                Detection.detected_at >= today_start
            ).scalar() or 0

            most_common = session.query(
                Detection.waste_category, func.count(Detection.id).label("cnt")
            ).filter(
                Detection.detected_at >= today_start
            ).group_by(Detection.waste_category).order_by(
                func.count(Detection.id).desc()
            ).first()

            most_common_category = most_common[0] if most_common else "N/A"

            active_alerts = session.query(func.count(Alert.id)).filter(
                Alert.is_acknowledged == False
            ).scalar() or 0

            return {
                "total_today": total_today,
                "most_common_category": most_common_category,
                "active_alerts": active_alerts
            }
        except Exception:
            return {"total_today": 0, "most_common_category": "N/A", "active_alerts": 0}
        finally:
            session.close()

    def get_total_stats(self) -> dict:
        """Return all-time totals."""
        session = Session()
        try:
            total = session.query(func.count(Detection.id)).scalar() or 0

            most_common = session.query(
                Detection.waste_category, func.count(Detection.id).label("cnt")
            ).group_by(Detection.waste_category).order_by(
                func.count(Detection.id).desc()
            ).first()

            most_common_category = most_common[0] if most_common else "N/A"

            return {
                "total_detections": total,
                "most_common_category": most_common_category
            }
        except Exception:
            return {"total_detections": 0, "most_common_category": "N/A"}
        finally:
            session.close()

    def get_category_distribution(self, start_date=None, end_date=None) -> dict:
        """Return {category: count} for pie chart."""
        session = Session()
        try:
            query = session.query(
                Detection.waste_category, func.count(Detection.id)
            )
            if start_date:
                query = query.filter(Detection.detected_at >= start_date)
            if end_date:
                query = query.filter(Detection.detected_at <= end_date)

            results = query.group_by(Detection.waste_category).all()
            return {row[0]: row[1] for row in results}
        except Exception:
            return {}
        finally:
            session.close()

    def get_daily_counts(self, days: int = 7) -> list:
        """Return [{date, count}] for the last N days for bar chart."""
        session = Session()
        try:
            results = []
            for i in range(days - 1, -1, -1):
                day = datetime.utcnow().replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) - timedelta(days=i)
                next_day = day + timedelta(days=1)

                count = session.query(func.count(Detection.id)).filter(
                    Detection.detected_at >= day,
                    Detection.detected_at < next_day
                ).scalar() or 0

                results.append({
                    "date": day.strftime("%Y-%m-%d"),
                    "count": count
                })
            return results
        except Exception:
            return []
        finally:
            session.close()

    def get_trend_data(self, days: int = 30) -> list:
        """Return [{date, count}] for the last N days for line chart."""
        return self.get_daily_counts(days)

    def get_fill_level_distribution(self, start_date=None, end_date=None) -> dict:
        """Return {level: count} for fill level breakdown."""
        session = Session()
        try:
            query = session.query(
                Detection.bin_fill_level, func.count(Detection.id)
            )
            if start_date:
                query = query.filter(Detection.detected_at >= start_date)
            if end_date:
                query = query.filter(Detection.detected_at <= end_date)

            results = query.filter(
                Detection.bin_fill_level.isnot(None)
            ).group_by(Detection.bin_fill_level).all()

            return {row[0]: row[1] for row in results}
        except Exception:
            return {}
        finally:
            session.close()

    def get_operator_performance(self, start_date=None, end_date=None) -> list:
        """Return [{user, detection_count}] for operator performance."""
        session = Session()
        try:
            query = session.query(
                User.full_name, func.count(Detection.id).label("cnt")
            ).join(Detection, Detection.detected_by == User.id)

            if start_date:
                query = query.filter(Detection.detected_at >= start_date)
            if end_date:
                query = query.filter(Detection.detected_at <= end_date)

            results = query.group_by(User.id, User.full_name).order_by(
                func.count(Detection.id).desc()
            ).all()

            return [{"user": row[0], "detection_count": row[1]} for row in results]
        except Exception:
            return []
        finally:
            session.close()
