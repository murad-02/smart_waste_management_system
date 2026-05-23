from datetime import datetime, timedelta

from sqlalchemy import func

from config import BIN_FILL_LEVELS
from database.db_setup import Session
from database.models import AlertRule, Alert, Detection
from core.notification_service import NotificationService


def _period_start(now: datetime, period: str):
    """Return the start of the current 'daily'/'weekly'/'monthly' window."""
    if period == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "weekly":
        start = now - timedelta(days=now.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "monthly":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return None


def _normalize_fill_level(value: str) -> str:
    """Normalize an arbitrary fill-level string into the canonical vocab."""
    if not value:
        return ""
    s = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if "overflow" in s:
        return "overflowing"
    if "almost" in s:
        return "almost_full"
    if "empty" in s:
        return "empty"
    if "half" in s or "medium" in s or "partial" in s:
        return "half"
    if "full" in s:
        return "full"
    return s


class AlertManager:
    """Manages alert rules and triggered alerts.

    Alert rules are keyed off of bin fill level (empty / half / almost_full /
    full / overflowing). Whenever the number of bins detected at a given fill
    level within the rule's period crosses the threshold, a single alert is
    raised (once per period per rule).
    """

    def __init__(self):
        self.notification_service = NotificationService()

    # ------------------------------------------------------------------
    # Rule CRUD
    # ------------------------------------------------------------------

    def create_rule(self, rule_name: str, category: str, threshold_value: int,
                    period: str, notify_email: str, created_by: int):
        """Create a new alert rule.

        ``category`` is the bin fill level the rule watches (stored in the
        existing ``category`` column for backward compatibility).
        """
        fill_level = _normalize_fill_level(category)
        if fill_level not in BIN_FILL_LEVELS:
            return None

        session = Session()
        try:
            rule = AlertRule(
                rule_name=rule_name,
                category=fill_level,
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
        if "category" in kwargs and kwargs["category"]:
            fl = _normalize_fill_level(kwargs["category"])
            if fl not in BIN_FILL_LEVELS:
                return False
            kwargs["category"] = fl

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

    def delete_rule(self, rule_id: int):
        """Delete an alert rule and any alerts it produced.

        Alerts hold a NOT NULL foreign key to the rule, so we must clear
        them explicitly — the relationship has no cascade configured.

        Returns (success, message). ``message`` is None on success.
        """
        session = Session()
        try:
            rule = session.query(AlertRule).filter_by(id=rule_id).first()
            if not rule:
                return False, f"Rule #{rule_id} not found."

            session.query(Alert).filter(Alert.rule_id == rule_id).delete(
                synchronize_session=False
            )
            session.delete(rule)
            session.commit()
            return True, None
        except Exception as e:
            session.rollback()
            return False, f"Database error: {e}"
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

    # ------------------------------------------------------------------
    # Triggering
    # ------------------------------------------------------------------

    def check_alerts(self) -> list:
        """Check all active rules against current fill-level detection counts.

        Called after every detection. Returns a list of newly triggered alerts.
        Each triggered alert is committed BEFORE the (potentially slow / failure-
        prone) email send, so SMTP problems can never swallow a triggered alert.
        """
        triggered_to_email = []  # (notify_email, subject, body)
        triggered = []

        session = Session()
        try:
            rules = session.query(AlertRule).filter_by(is_active=True).all()

            for rule in rules:
                fill_level = _normalize_fill_level(rule.category)
                if fill_level not in BIN_FILL_LEVELS:
                    continue

                now = datetime.utcnow()
                start = _period_start(now, rule.period)
                if start is None:
                    continue

                # Count bins detected at this fill level inside the period.
                count = session.query(func.count(Detection.id)).filter(
                    func.lower(Detection.bin_fill_level) == fill_level,
                    Detection.detected_at >= start
                ).scalar() or 0

                if count < rule.threshold_value:
                    continue

                # One alert per rule per day, regardless of how many detections
                # come in afterwards.
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                existing = session.query(Alert).filter(
                    Alert.rule_id == rule.id,
                    Alert.triggered_at >= today_start
                ).first()
                if existing:
                    continue

                severity = self._severity_for(fill_level, count, rule.threshold_value)
                fill_disp = fill_level.replace("_", " ")
                message = (
                    f"{rule.rule_name}: {count} bin(s) detected at "
                    f"\"{fill_disp}\" fill level ({rule.period})."
                )

                alert = Alert(
                    rule_id=rule.id,
                    message=message,
                    severity=severity,
                    is_acknowledged=False,
                    triggered_at=now,
                )
                session.add(alert)
                session.flush()
                session.refresh(alert)
                alert_id = alert.id

                triggered.append({
                    "alert_id": alert_id,
                    "message": message,
                    "severity": severity,
                    "rule_name": rule.rule_name,
                    "fill_level": fill_level,
                })

                if rule.notify_email:
                    subject = f"[SWMS ALERT] {rule.rule_name} — {severity}"
                    body = self._format_email_body(
                        rule.rule_name, fill_level, count,
                        rule.threshold_value, rule.period, severity, now
                    )
                    triggered_to_email.append((rule.notify_email, subject, body))

            session.commit()
        except Exception:
            session.rollback()
            triggered = []
            triggered_to_email = []
        finally:
            session.close()

        # Email *after* the transaction commits — a slow or failing SMTP can no
        # longer wipe out alerts the user already saw triggered.
        for to_email, subject, body in triggered_to_email:
            try:
                self.notification_service.send_email(to_email, subject, body)
            except Exception:
                pass

        return triggered

    @staticmethod
    def _severity_for(fill_level: str, count: int, threshold: int) -> str:
        """Pick a severity that makes sense for the fill level + scale."""
        if fill_level in ("overflowing", "full"):
            return "critical"
        if fill_level == "almost_full":
            return "warning"
        if threshold > 0 and (count / threshold) >= 2.0:
            return "warning"
        return "info"

    @staticmethod
    def _format_email_body(rule_name, fill_level, count, threshold,
                           period, severity, when) -> str:
        fill_disp = fill_level.replace("_", " ").title()
        return (
            f"Alert Details:\n"
            f"- Rule: {rule_name}\n"
            f"- Fill Level: {fill_disp}\n"
            f"- Current Count: {count} / Threshold: {threshold}\n"
            f"- Period: {period}\n"
            f"- Severity: {severity}\n"
            f"- Time: {when.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"\nPlease take immediate action.\n"
            f"\n— Smart Waste Management System"
        )

    # ------------------------------------------------------------------
    # Alert queries / acknowledgement
    # ------------------------------------------------------------------

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

    def send_test_alert(self, rule_id: int):
        """Force-trigger an alert for a rule, bypassing count/dedup.

        Creates an Alert record (severity='info') and sends the configured
        notification email immediately. The alert row is committed BEFORE the
        email is sent. Returns (success, message).
        """
        session = Session()
        notify_email = None
        subject = body = None
        try:
            rule = session.query(AlertRule).filter_by(id=rule_id).first()
            if not rule:
                return False, f"Rule #{rule_id} not found."

            fill_level = _normalize_fill_level(rule.category)
            if fill_level not in BIN_FILL_LEVELS:
                return False, (
                    f"Rule has invalid fill level '{rule.category}'. "
                    f"Expected one of: {', '.join(BIN_FILL_LEVELS)}."
                )

            now = datetime.utcnow()
            start = _period_start(now, rule.period) or now
            count = session.query(func.count(Detection.id)).filter(
                func.lower(Detection.bin_fill_level) == fill_level,
                Detection.detected_at >= start
            ).scalar() or 0

            fill_disp = fill_level.replace("_", " ")
            message = (
                f"[TEST] {rule.rule_name}: {count} bin(s) currently at "
                f"\"{fill_disp}\" fill level ({rule.period})."
            )
            alert = Alert(
                rule_id=rule.id,
                message=message,
                severity="info",
                is_acknowledged=False,
                triggered_at=now,
            )
            session.add(alert)
            session.flush()
            session.refresh(alert)

            notify_email = rule.notify_email
            if notify_email:
                subject = f"[SWMS TEST] {rule.rule_name}"
                body = self._format_email_body(
                    rule.rule_name, fill_level, count,
                    rule.threshold_value, rule.period, "info", now
                )

            session.commit()
        except Exception as e:
            session.rollback()
            return False, f"Database error: {e}"
        finally:
            session.close()

        if not notify_email:
            return True, "Test alert recorded, but no notify_email is set on this rule."

        ok = self.notification_service.send_email(notify_email, subject, body)
        if ok:
            return True, f"Test alert sent to {notify_email}."
        return False, (
            "Test alert recorded, but the email failed to send. "
            "Open Settings → SMTP → Test Connection to see the SMTP error."
        )

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
