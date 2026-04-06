from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime, Date,
    ForeignKey, create_engine
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    role = Column(String(20), nullable=False, default="operator")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    detections = relationship("Detection", back_populates="operator", foreign_keys="Detection.detected_by")
    verified_detections = relationship("Detection", back_populates="verifier", foreign_keys="Detection.verified_by")
    activity_logs = relationship("ActivityLog", back_populates="user")
    alert_rules = relationship("AlertRule", back_populates="creator")
    acknowledged_alerts = relationship("Alert", back_populates="acknowledger")
    reports = relationship("Report", back_populates="generator")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_path = Column(String(500), nullable=False)
    result_image_path = Column(String(500), nullable=True)
    waste_category = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    bin_fill_level = Column(String(20), nullable=True)
    detected_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    # Relationships
    operator = relationship("User", back_populates="detections", foreign_keys=[detected_by])
    verifier = relationship("User", back_populates="verified_detections", foreign_keys=[verified_by])

    def __repr__(self):
        return f"<Detection(id={self.id}, category='{self.waste_category}', confidence={self.confidence})>"


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    threshold_value = Column(Integer, nullable=False)
    period = Column(String(20), nullable=False)
    notify_email = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    creator = relationship("User", back_populates="alert_rules")
    alerts = relationship("Alert", back_populates="rule")

    def __repr__(self):
        return f"<AlertRule(id={self.id}, name='{self.rule_name}')>"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=False)
    message = Column(String(500), nullable=False)
    severity = Column(String(20), nullable=False)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    triggered_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    rule = relationship("AlertRule", back_populates="alerts")
    acknowledger = relationship("User", back_populates="acknowledged_alerts")

    def __repr__(self):
        return f"<Alert(id={self.id}, severity='{self.severity}')>"


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(200), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="activity_logs")

    def __repr__(self):
        return f"<ActivityLog(id={self.id}, action='{self.action}')>"


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(50), nullable=False)
    file_path = Column(String(500), nullable=False)
    generated_by = Column(Integer, ForeignKey("users.id"))
    generated_at = Column(DateTime, default=datetime.utcnow)
    date_range_start = Column(Date, nullable=False)
    date_range_end = Column(Date, nullable=False)

    # Relationships
    generator = relationship("User", back_populates="reports")

    def __repr__(self):
        return f"<Report(id={self.id}, type='{self.report_type}')>"


class AppSetting(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AppSetting(key='{self.key}', value='{self.value}')>"
