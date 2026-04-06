from datetime import datetime
import bcrypt

from database.db_setup import Session
from database.models import User


class AuthManager:
    """Handles authentication, user management, and role-based access control."""

    ROLE_HIERARCHY = {"admin": 3, "supervisor": 2, "operator": 1}

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against a bcrypt hash."""
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

    def _make_detached(self, user, session):
        """Eagerly load all attributes so the user can be used outside the session."""
        # Access all columns to load them into the instance state
        _ = user.id, user.username, user.password_hash, user.full_name
        _ = user.email, user.role, user.is_active, user.created_at, user.last_login
        session.expunge(user)
        return user

    def login(self, username: str, password: str):
        """Verify credentials and return User object or None."""
        session = Session()
        try:
            user = session.query(User).filter_by(username=username, is_active=True).first()
            if user and self.verify_password(password, user.password_hash):
                user.last_login = datetime.utcnow()
                session.commit()
                return self._make_detached(user, session)
            return None
        except Exception:
            session.rollback()
            return None
        finally:
            session.close()

    def create_user(self, username: str, password: str, full_name: str,
                    email: str, role: str, created_by_id: int):
        """Create a new user. Returns User object or error message string."""
        session = Session()
        try:
            existing = session.query(User).filter_by(username=username).first()
            if existing:
                return f"Username '{username}' already exists."

            new_user = User(
                username=username,
                password_hash=self.hash_password(password),
                full_name=full_name,
                email=email if email else None,
                role=role,
                is_active=True,
                created_at=datetime.utcnow()
            )
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            return self._make_detached(new_user, session)
        except Exception as e:
            session.rollback()
            return str(e)
        finally:
            session.close()

    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user fields (full_name, email, role, is_active, password_hash)."""
        session = Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return False

            allowed_fields = {"full_name", "email", "role", "is_active", "password_hash"}
            for key, value in kwargs.items():
                if key in allowed_fields:
                    setattr(user, key, value)

            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def deactivate_user(self, user_id: int, admin_id: int):
        """Soft-delete a user. Prevents self-deactivation. Returns bool or error string."""
        if user_id == admin_id:
            return "You cannot deactivate your own account."

        session = Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return "User not found."

            user.is_active = False
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            return str(e)
        finally:
            session.close()

    def activate_user(self, user_id: int) -> bool:
        """Re-activate a deactivated user."""
        session = Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return False
            user.is_active = True
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def get_all_users(self):
        """Return all users."""
        session = Session()
        try:
            users = session.query(User).all()
            for u in users:
                self._make_detached(u, session)
            return users
        except Exception:
            return []
        finally:
            session.close()

    def get_user_by_id(self, user_id: int):
        """Return a user by ID or None."""
        session = Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                return self._make_detached(user, session)
            return user
        except Exception:
            return None
        finally:
            session.close()

    def check_permission(self, user, required_role: str) -> bool:
        """Check if user's role meets or exceeds the required role level."""
        user_level = self.ROLE_HIERARCHY.get(user.role, 0)
        required_level = self.ROLE_HIERARCHY.get(required_role, 0)
        return user_level >= required_level
