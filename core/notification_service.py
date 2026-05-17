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
        """Send an email using SMTP settings. Returns True/False (legacy API)."""
        ok, _ = self.send_email_verbose(to_email, subject, body)
        return ok

    def send_email_verbose(self, to_email: str, subject: str, body: str):
        """Send an email and return (success, error_message).

        error_message is None on success, otherwise a human-readable reason.
        Use this in the Settings 'Test Connection' button so failures surface
        the actual SMTP error instead of a generic 'failed' toast.
        """
        settings = self._get_smtp_settings()

        if not settings["smtp_server"]:
            return False, "SMTP server is not configured."
        if not settings["smtp_email"]:
            return False, "Sender email is not configured."
        if not settings["smtp_password"]:
            return False, "SMTP password is not configured."

        try:
            port = int(settings["smtp_port"]) if settings["smtp_port"] else 587
        except ValueError:
            return False, f"Invalid SMTP port: {settings['smtp_port']!r}"

        msg = MIMEMultipart()
        msg["From"] = settings["smtp_email"]
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            if port == 465:
                # Implicit TLS (SMTPS)
                with smtplib.SMTP_SSL(settings["smtp_server"], port, timeout=15) as server:
                    server.login(settings["smtp_email"], settings["smtp_password"])
                    server.send_message(msg)
            else:
                # STARTTLS (587 / 25)
                with smtplib.SMTP(settings["smtp_server"], port, timeout=15) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(settings["smtp_email"], settings["smtp_password"])
                    server.send_message(msg)
            return True, None
        except smtplib.SMTPAuthenticationError as e:
            code = getattr(e, "smtp_code", "")
            reason = ""
            try:
                reason = e.smtp_error.decode("utf-8", errors="ignore")
            except Exception:
                reason = str(e)
            return False, (
                f"Authentication failed ({code}). For Gmail you must use a "
                f"16-char App Password (not your normal password), and "
                f"2-Step Verification must be enabled. Server said: {reason}"
            )
        except smtplib.SMTPRecipientsRefused as e:
            return False, f"Recipient address refused: {e.recipients}"
        except smtplib.SMTPSenderRefused as e:
            return False, f"Sender address refused: {e.sender} ({e.smtp_error})"
        except smtplib.SMTPConnectError as e:
            return False, f"Could not connect to {settings['smtp_server']}:{port}: {e}"
        except (smtplib.SMTPServerDisconnected, smtplib.SMTPException) as e:
            return False, f"SMTP error: {e}"
        except OSError as e:
            return False, f"Network error: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"

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
