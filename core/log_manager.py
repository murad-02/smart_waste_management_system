from datetime import datetime

from database.db_setup import Session
from database.models import ActivityLog


class LogManager:
    """Handles activity logging to the database."""

    def log_activity(self, user_id: int, action: str, details: str = None):
        """Save an activity log entry to the database."""
        session = Session()
        try:
            log = ActivityLog(
                user_id=user_id,
                action=action,
                details=details,
                timestamp=datetime.utcnow()
            )
            session.add(log)
            session.commit()
            session.refresh(log)
            session.expunge(log)
            return log
        except Exception:
            session.rollback()
            return None
        finally:
            session.close()

    def get_logs(self, user_id: int = None, start_date=None, end_date=None, limit: int = 100):
        """Retrieve activity logs with optional filters."""
        session = Session()
        try:
            query = session.query(ActivityLog)

            if user_id is not None:
                query = query.filter(ActivityLog.user_id == user_id)
            if start_date is not None:
                query = query.filter(ActivityLog.timestamp >= start_date)
            if end_date is not None:
                query = query.filter(ActivityLog.timestamp <= end_date)

            query = query.order_by(ActivityLog.timestamp.desc()).limit(limit)
            logs = query.all()
            session.expunge_all()
            return logs
        except Exception:
            return []
        finally:
            session.close()
