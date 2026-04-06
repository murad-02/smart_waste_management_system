import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from database.db_setup import Session
from database.models import AppSetting


class NotificationService:
    """Handles email notifications using SMTP settings from the database."""

    def _get_smtp_settings(self) -> dict:
        """Load SMTP settings from app_settings table."""
        session = Session()
        try:
            settings = {}
            for key in ["smtp_server", "smtp_port", "smtp_email", "smtp_password"]:
                row = session.query(AppSetting).filter_by(key=key).first()
                settings[key] = row.value if row else ""
            return settings
        except Exception:
            return {"smtp_server": "", "smtp_port": "587",
                    "smtp_email": "", "smtp_password": ""}
        finally:
            session.close()

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send an email using SMTP settings from app_settings."""
        settings = self._get_smtp_settings()

        if not settings["smtp_server"] or not settings["smtp_email"]:
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = settings["smtp_email"]
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            port = int(settings["smtp_port"]) if settings["smtp_port"] else 587

            with smtplib.SMTP(settings["smtp_server"], port, timeout=10) as server:
                server.starttls()
                server.login(settings["smtp_email"], settings["smtp_password"])
                server.send_message(msg)

            return True
        except Exception:
            return False

    def send_bin_full_alert(self, alert, rule, count: int = 0) -> bool:
        """Send a formatted bin full alert email."""
        if not rule.notify_email:
            return False

        subject = f"[SWMS ALERT] {rule.rule_name} — {alert.severity}"
        body = (
            f"Alert Details:\n"
            f"- Category: {rule.category}\n"
            f"- Current Count: {count} / Threshold: {rule.threshold_value}\n"
            f"- Period: {rule.period}\n"
            f"- Severity: {alert.severity}\n"
            f"- Time: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S') if alert.triggered_at else datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"\nPlease take immediate action.\n"
            f"\n— Smart Waste Management System"
        )

        return self.send_email(rule.notify_email, subject, body)
