"""Truck CRUD + business logic.

Mirrors the session-handling pattern used by core.auth_manager — services
own session lifecycle and return detached ORM instances so the UI layer
never has to think about SQLAlchemy.
"""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import or_

from database.db_setup import Session
from database.fleet_models import Truck
from core.log_manager import LogManager
from core.fleet.constants import TRUCK_STATUSES, FUEL_TYPES
from core.fleet.fleet_permissions import require

logger = logging.getLogger(__name__)


class TruckService:
    """Service layer for truck management."""

    def __init__(self):
        self.log = LogManager()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _detach(truck: Truck, session) -> Truck:
        # Touch every column we expose to load it before expunge.
        _ = (truck.id, truck.truck_code, truck.plate_number, truck.capacity,
             truck.fuel_type, truck.status, truck.assigned_zone,
             truck.purchase_date, truck.notes, truck.is_active,
             truck.created_at, truck.updated_at)
        session.expunge(truck)
        return truck

    @staticmethod
    def _validate(data: dict, *, is_update: bool = False):
        if not is_update or "truck_code" in data:
            code = (data.get("truck_code") or "").strip()
            if not code:
                raise ValueError("Truck code is required.")
            if len(code) > 30:
                raise ValueError("Truck code must be 30 characters or fewer.")
        if not is_update or "plate_number" in data:
            plate = (data.get("plate_number") or "").strip()
            if not plate:
                raise ValueError("Plate number is required.")
        if "capacity" in data and data["capacity"] is not None:
            try:
                if float(data["capacity"]) < 0:
                    raise ValueError("Capacity cannot be negative.")
            except (TypeError, ValueError):
                raise ValueError("Capacity must be a number.")
        if "status" in data and data["status"] not in TRUCK_STATUSES:
            raise ValueError(f"Invalid truck status: {data['status']!r}.")
        if "fuel_type" in data and data["fuel_type"] not in FUEL_TYPES:
            raise ValueError(f"Invalid fuel type: {data['fuel_type']!r}.")

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def list_trucks(self, *, search: str = "", status: Optional[str] = None,
                    include_inactive: bool = False) -> List[Truck]:
        session = Session()
        try:
            q = session.query(Truck)
            if not include_inactive:
                q = q.filter(Truck.is_active.is_(True))
            if status:
                q = q.filter(Truck.status == status)
            if search:
                like = f"%{search.strip()}%"
                q = q.filter(or_(
                    Truck.truck_code.ilike(like),
                    Truck.plate_number.ilike(like),
                    Truck.assigned_zone.ilike(like),
                ))
            q = q.order_by(Truck.truck_code.asc())
            trucks = q.all()
            for t in trucks:
                self._detach(t, session)
            return trucks
        finally:
            session.close()

    def get(self, truck_id: int) -> Optional[Truck]:
        session = Session()
        try:
            truck = session.query(Truck).filter_by(id=truck_id).first()
            return self._detach(truck, session) if truck else None
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------
    def create(self, actor, data: dict) -> Truck:
        require(actor, "truck.create")
        self._validate(data)
        session = Session()
        try:
            # Uniqueness checks
            for field in ("truck_code", "plate_number"):
                existing = session.query(Truck).filter(
                    getattr(Truck, field) == data[field]
                ).first()
                if existing:
                    raise ValueError(f"{field.replace('_', ' ').title()} "
                                     f"'{data[field]}' already exists.")

            truck = Truck(
                truck_code=data["truck_code"].strip(),
                plate_number=data["plate_number"].strip(),
                capacity=float(data.get("capacity") or 0.0),
                fuel_type=data.get("fuel_type") or "diesel",
                status=data.get("status") or "available",
                assigned_zone=(data.get("assigned_zone") or "").strip() or None,
                purchase_date=data.get("purchase_date"),
                notes=(data.get("notes") or "").strip() or None,
            )
            session.add(truck)
            session.commit()
            session.refresh(truck)
            self._detach(truck, session)

            self.log.log_activity(actor.id, "truck_created",
                                  f"Created truck '{truck.truck_code}' ({truck.plate_number})")
            logger.info("Truck %s created by user %s", truck.id, actor.id)
            return truck
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update(self, actor, truck_id: int, data: dict) -> Truck:
        require(actor, "truck.edit")
        self._validate(data, is_update=True)
        session = Session()
        try:
            truck = session.query(Truck).filter_by(id=truck_id).first()
            if not truck:
                raise ValueError(f"Truck #{truck_id} not found.")

            updatable = {"truck_code", "plate_number", "capacity", "fuel_type",
                         "status", "assigned_zone", "purchase_date", "notes"}
            for key, value in data.items():
                if key in updatable:
                    if isinstance(value, str):
                        value = value.strip() or None
                    setattr(truck, key, value)
            truck.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(truck)
            self._detach(truck, session)

            self.log.log_activity(actor.id, "truck_updated",
                                  f"Updated truck '{truck.truck_code}'")
            return truck
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def soft_delete(self, actor, truck_id: int) -> bool:
        require(actor, "truck.delete")
        session = Session()
        try:
            truck = session.query(Truck).filter_by(id=truck_id).first()
            if not truck:
                raise ValueError(f"Truck #{truck_id} not found.")
            truck.is_active = False
            truck.status = "inactive"
            session.commit()
            self.log.log_activity(actor.id, "truck_deactivated",
                                  f"Deactivated truck '{truck.truck_code}'")
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def restore(self, actor, truck_id: int) -> bool:
        require(actor, "truck.edit")
        session = Session()
        try:
            truck = session.query(Truck).filter_by(id=truck_id).first()
            if not truck:
                return False
            truck.is_active = True
            truck.status = "available"
            session.commit()
            self.log.log_activity(actor.id, "truck_restored",
                                  f"Restored truck '{truck.truck_code}'")
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()
