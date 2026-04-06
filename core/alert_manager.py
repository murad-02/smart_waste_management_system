from datetime import datetime, timedelta

from sqlalchemy import func

from database.db_setup import Session
from database.models import AlertRule, Alert, Detection
from core.notification_service import NotificationService


class AlertManager:
    """Manages alert rules and triggered alerts."""

    def __init__(self):
        self.notification_service = NotificationService()

    def create_rule(self, rule_name: str, category: str, threshold_value: int,
                    period: str, notify_email: str, created_by: int):
        """Create a new alert rule."""
        session = Session()
        try:
            rule = AlertRule(
                rule_name=rule_name,
                category=category,
                threshold_value=threshold_value,
                period=period,
                notify_email=notify_email if notify_email else None,
                is_active=True,
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            session.add(rule)
            session.commit()
            session.refresh(rule)
            session.expunge(rule)
            return rule
        except Exception:
            session.rollback()
            return None
        finally:
            session.close()

    def update_rule(self, rule_id: int, **kwargs) -> bool:
        """Update an alert rule's fields."""
        session = Session()
        try:
            rule = session.query(AlertRule).filter_by(id=rule_id).first()
            if not rule:
                return False

            allowed_fields = {"rule_name", "category", "threshold_value",
                              "period", "notify_email", "is_active"}
            for key, value in kwargs.items():
                if key in allowed_fields:
                    setattr(rule, key, value)

            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def delete_rule(self, rule_id: int) -> bool:
        """Delete an alert rule."""
        session = Session()
        try:
            rule = session.query(AlertRule).filter_by(id=rule_id).first()
            if not rule:
                return False
            session.delete(rule)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def get_all_rules(self):
        """Return all alert rules."""
        session = Session()
        try:
            rules = session.query(AlertRule).order_by(AlertRule.created_at.desc()).all()
            session.expunge_all()
            return rules
        except Exception:
            return []
        finally:
            session.close()

    def check_alerts(self) -> list:
        """Check all active rules against current detection counts.

        Called after every detection. Returns list of newly triggered alerts.
        """
        session = Session()
        triggered = []
        try:
            rules = session.query(AlertRule).filter_by(is_active=True).all()

            for rule in rules:
                # Determine the time window based on the period
                now = datetime.utcnow()
                if rule.period == "daily":
                    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                elif rule.period == "weekly":
                    start = now - timedelta(days=now.weekday())
                    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
                elif rule.period == "monthly":
                    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                else:
                    continue

                # Count detections for this category in the period
                count = session.query(func.count(Detection.id)).filter(
                    Detection.waste_category == rule.category,
                    Detection.detected_at >= start
                ).scalar() or 0

                if count >= rule.threshold_value:
                    # Check if we already triggered an alert for this rule today
                    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    existing = session.query(Alert).filter(
                        Alert.rule_id == rule.id,
                        Alert.triggered_at >= today_start
                    ).first()

                    if not existing:
                        # Determine severity
                        ratio = count / rule.threshold_value
                        if ratio >= 2.0:
                            severity = "critical"
                        elif ratio >= 1.5:
                            severity = "warning"
                        else:
                            severity = "info"

                        message = (
                            f"Alert: {rule.rule_name} — {rule.category} detections "
                            f"reached {count}/{rule.threshold_value} ({rule.period})"
                        )

                        alert = Alert(
                            rule_id=rule.id,
                            message=message,
                            severity=severity,
                            is_acknowledged=False,
                            triggered_at=datetime.utcnow()
                        )
                        session.add(alert)
                        session.flush()
                        session.refresh(alert)

                        triggered.append({
                            "alert_id": alert.id,
                            "message": message,
                            "severity": severity,
                            "rule_name": rule.rule_name
                        })

                        # Send email notification if configured
                        if rule.notify_email:
                            session.expunge(alert)
                            rule_copy = AlertRule(
                                rule_name=rule.rule_name,
                                category=rule.category,
                                threshold_value=rule.threshold_value,
                                period=rule.period,
                                notify_email=rule.notify_email
                            )
                            self.notification_service.send_bin_full_alert(
                                alert, rule_copy, count
                            )

            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

        return triggered

    def get_alerts(self, acknowledged: bool = None):
        """Get alerts, optionally filtered by acknowledgment status."""
        session = Session()
        try:
            query = session.query(Alert)
            if acknowledged is not None:
                query = query.filter(Alert.is_acknowledged == acknowledged)
            alerts = query.order_by(Alert.triggered_at.desc()).all()
            session.expunge_all()
            return alerts
        except Exception:
            return []
        finally:
            session.close()

    def acknowledge_alert(self, alert_id: int, user_id: int) -> bool:
        """Mark an alert as acknowledged."""
        session = Session()
        try:
            alert = session.query(Alert).filter_by(id=alert_id).first()
            if not alert:
                return False
            alert.is_acknowledged = True
            alert.acknowledged_by = user_id
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
