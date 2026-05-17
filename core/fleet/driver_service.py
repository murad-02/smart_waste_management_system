"""Driver CRUD + truck-assignment helpers."""

import logging
import re
from datetime import datetime
from typing import List, Optional

from sqlalchemy import or_

from database.db_setup import Session
from database.fleet_models import Driver, Truck
from core.log_manager import LogManager
from core.fleet.constants import DRIVER_STATUSES
from core.fleet.fleet_permissions import require

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[+\d][\d\s\-()]{5,}$")


class DriverService:
    def __init__(self):
        self.log = LogManager()

    # ------------------------------------------------------------------
    @staticmethod
    def _detach(driver: Driver, session) -> Driver:
        _ = (driver.id, driver.name, driver.phone, driver.email,
             driver.license_number, driver.assigned_truck_id,
             driver.status, driver.is_active,
             driver.created_at, driver.updated_at)
        # Eagerly load truck label if any
        if driver.truck is not None:
            _ = (driver.truck.id, driver.truck.truck_code, driver.truck.plate_number)
        session.expunge(driver)
        return driver

    @staticmethod
    def _validate(data: dict, *, is_update: bool = False):
        if not is_update or "name" in data:
            if not (data.get("name") or "").strip():
                raise ValueError("Driver name is required.")
        if not is_update or "license_number" in data:
            if not (data.get("license_number") or "").strip():
                raise ValueError("License number is required.")
        if data.get("email"):
            if not EMAIL_RE.match(data["email"].strip()):
                raise ValueError("Email is not a valid address.")
        if data.get("phone"):
            if not PHONE_RE.match(data["phone"].strip()):
                raise ValueError("Phone number is not valid.")
        if "status" in data and data["status"] not in DRIVER_STATUSES:
            raise ValueError(f"Invalid driver status: {data['status']!r}.")

    # ------------------------------------------------------------------
    def list_drivers(self, *, search: str = "", status: Optional[str] = None,
                     include_inactive: bool = False) -> List[Driver]:
        session = Session()
        try:
            q = session.query(Driver)
            if not include_inactive:
                q = q.filter(Driver.is_active.is_(True))
            if status:
                q = q.filter(Driver.status == status)
            if search:
                like = f"%{search.strip()}%"
                q = q.filter(or_(
                    Driver.name.ilike(like),
                    Driver.license_number.ilike(like),
                    Driver.phone.ilike(like),
                    Driver.email.ilike(like),
                ))
            q = q.order_by(Driver.name.asc())
            drivers = q.all()
            for d in drivers:
                self._detach(d, session)
            return drivers
        finally:
            session.close()

    def get(self, driver_id: int) -> Optional[Driver]:
        session = Session()
        try:
            driver = session.query(Driver).filter_by(id=driver_id).first()
            return self._detach(driver, session) if driver else None
        finally:
            session.close()

    # ------------------------------------------------------------------
    def create(self, actor, data: dict) -> Driver:
        require(actor, "driver.create")
        self._validate(data)
        session = Session()
        try:
            existing = session.query(Driver).filter_by(
                license_number=data["license_number"].strip()
            ).first()
            if existing:
                raise ValueError(
                    f"License number '{data['license_number']}' already exists."
                )

            truck_id = data.get("assigned_truck_id") or None
            if truck_id:
                self._check_truck_assignable(session, truck_id)

            driver = Driver(
                name=data["name"].strip(),
                phone=(data.get("phone") or "").strip() or None,
                email=(data.get("email") or "").strip() or None,
                license_number=data["license_number"].strip(),
                assigned_truck_id=truck_id,
                status=data.get("status") or "available",
            )
            session.add(driver)
            session.commit()
            session.refresh(driver)
            self._detach(driver, session)

            self.log.log_activity(actor.id, "driver_created",
                                  f"Created driver '{driver.name}' (license "
                                  f"{driver.license_number})")
            return driver
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update(self, actor, driver_id: int, data: dict) -> Driver:
        require(actor, "driver.edit")
        self._validate(data, is_update=True)
        session = Session()
        try:
            driver = session.query(Driver).filter_by(id=driver_id).first()
            if not driver:
                raise ValueError(f"Driver #{driver_id} not found.")

            truck_id = data.get("assigned_truck_id")
            if truck_id and truck_id != driver.assigned_truck_id:
                self._check_truck_assignable(session, truck_id)

            updatable = {"name", "phone", "email", "license_number",
                         "assigned_truck_id", "status"}
            for key, value in data.items():
                if key in updatable:
                    if isinstance(value, str):
                        value = value.strip() or None
                    setattr(driver, key, value)
            driver.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(driver)
            self._detach(driver, session)

            self.log.log_activity(actor.id, "driver_updated",
                                  f"Updated driver '{driver.name}'")
            return driver
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def soft_delete(self, actor, driver_id: int) -> bool:
        require(actor, "driver.delete")
        session = Session()
        try:
            driver = session.query(Driver).filter_by(id=driver_id).first()
            if not driver:
                raise ValueError(f"Driver #{driver_id} not found.")
            driver.is_active = False
            driver.assigned_truck_id = None
            session.commit()
            self.log.log_activity(actor.id, "driver_deactivated",
                                  f"Deactivated driver '{driver.name}'")
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def restore(self, actor, driver_id: int) -> bool:
        require(actor, "driver.edit")
        session = Session()
        try:
            driver = session.query(Driver).filter_by(id=driver_id).first()
            if not driver:
                return False
            driver.is_active = True
            session.commit()
            self.log.log_activity(actor.id, "driver_restored",
                                  f"Restored driver '{driver.name}'")
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    # ------------------------------------------------------------------
    @staticmethod
    def _check_truck_assignable(session, truck_id: int):
        truck = session.query(Truck).filter_by(id=truck_id,
                                               is_active=True).first()
        if not truck:
            raise ValueError(f"Truck #{truck_id} is not available for assignment.")
