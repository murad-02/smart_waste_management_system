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

    def get_status_breakdown(self) -> dict:
        """Return {pending, verified, rejected} counts across all detections."""
        session = Session()
        try:
            rows = session.query(
                Detection.status, func.count(Detection.id)
            ).group_by(Detection.status).all()
            result = {"pending": 0, "verified": 0, "rejected": 0}
            for status, count in rows:
                if status in result:
                    result[status] = count
            return result
        except Exception:
            return {"pending": 0, "verified": 0, "rejected": 0}
        finally:
            session.close()

    def get_avg_confidence(self, days: int = None) -> float:
        """Return average confidence (0-1). Optionally restrict to last N days."""
        session = Session()
        try:
            query = session.query(func.avg(Detection.confidence))
            if days is not None and days > 0:
                cutoff = datetime.utcnow() - timedelta(days=days)
                query = query.filter(Detection.detected_at >= cutoff)
            value = query.scalar()
            return float(value) if value is not None else 0.0
        except Exception:
            return 0.0
        finally:
            session.close()

    def get_week_count(self) -> int:
        """Return total detections in the last 7 days (rolling)."""
        session = Session()
        try:
            cutoff = datetime.utcnow() - timedelta(days=7)
            count = session.query(func.count(Detection.id)).filter(
                Detection.detected_at >= cutoff
            ).scalar() or 0
            return int(count)
        except Exception:
            return 0
        finally:
            session.close()

    def get_last_detection_time(self):
        """Return the datetime of the most recent detection, or None."""
        session = Session()
        try:
            value = session.query(func.max(Detection.detected_at)).scalar()
            return value
        except Exception:
            return None
        finally:
            session.close()

    def get_recent_detections(self, limit: int = 8) -> list:
        """Return the most recent N detections as plain dicts."""
        session = Session()
        try:
            rows = session.query(Detection, User.full_name).outerjoin(
                User, Detection.detected_by == User.id
            ).order_by(Detection.detected_at.desc()).limit(limit).all()

            results = []
            for det, full_name in rows:
                results.append({
                    "id": det.id,
                    "fill_level": det.bin_fill_level or "",
                    "confidence": float(det.confidence or 0.0),
                    "status": det.status or "pending",
                    "detected_at": det.detected_at,
                    "operator": full_name or f"User #{det.detected_by}",
                })
            return results
        except Exception:
            return []
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
