import os
import sys
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATABASE_PATH
from database.models import Base, User, AppSetting

# Ensure database directory exists
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

# Create engine
engine = create_engine(f"sqlite:///{DATABASE_PATH}", echo=False)

# Create session factory
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


def get_session():
    """Return a new database session."""
    return Session()


def init_db():
    """Initialize the database: create tables, seed default admin and settings."""
    import bcrypt

    # Create all tables
    Base.metadata.create_all(engine)

    session = Session()
    try:
        # Check if any admin user exists
        admin_exists = session.query(User).filter_by(role="admin").first()
        if not admin_exists:
            # Create default admin account
            password_hash = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            default_admin = User(
                username="admin",
                password_hash=password_hash,
                full_name="System Administrator",
                email=None,
                role="admin",
                is_active=True,
                created_at=datetime.utcnow()
            )
            session.add(default_admin)
            session.commit()
            print("Default admin user created (username: admin, password: admin123)")

        # Seed default app settings
        default_settings = {
            "smtp_server": "",
            "smtp_port": "587",
            "smtp_email": "",
            "smtp_password": "",
            "alert_check_enabled": "true",
            "company_name": "Smart Waste Management",
        }

        for key, value in default_settings.items():
            existing = session.query(AppSetting).filter_by(key=key).first()
            if not existing:
                setting = AppSetting(
                    key=key,
                    value=value,
                    updated_at=datetime.utcnow()
                )
                session.add(setting)

        session.commit()
        print("Database initialized successfully.")

    except Exception as e:
        session.rollback()
        print(f"Error initializing database: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    init_db()
