"""Maintenance log + upcoming-service reminders."""

import logging
from datetime import datetime, date, timedelta
from typing import List, Optional

from sqlalchemy.orm import joinedload

from database.db_setup import Session
from database.fleet_models import MaintenanceRecord, Truck
from core.log_manager import LogManager
from core.fleet.constants import MAINTENANCE_DUE_DAYS, SERVICE_TYPES
from core.fleet.fleet_permissions import require

logger = logging.getLogger(__name__)


class MaintenanceService:
    def __init__(self):
        self.log = LogManager()

    @staticmethod
    def _detach(record: MaintenanceRecord, session) -> MaintenanceRecord:
        _ = (record.id, record.truck_id, record.service_type,
             record.service_date, record.next_service_date,
             record.cost, record.notes,
             record.created_at, record.updated_at)
        if record.truck:
            _ = (record.truck.id, record.truck.truck_code,
                 record.truck.plate_number)
        session.expunge(record)
        return record

    @staticmethod
    def _validate(data: dict, *, is_update: bool = False):
        if not is_update and not data.get("truck_id"):
            raise ValueError("Truck is required.")
        if not is_update or "service_type" in data:
            stype = data.get("service_type")
            if not stype:
                raise ValueError("Service type is required.")
            if stype not in SERVICE_TYPES:
                raise ValueError(f"Invalid service type: {stype!r}.")
        if not is_update or "service_date" in data:
            if not data.get("service_date"):
                raise ValueError("Service date is required.")
        if data.get("cost") is not None:
            try:
                if float(data["cost"]) < 0:
                    raise ValueError("Cost cannot be negative.")
            except (TypeError, ValueError):
                raise ValueError("Cost must be a number.")
        if data.get("service_date") and data.get("next_service_date"):
            if data["next_service_date"] < data["service_date"]:
                raise ValueError("Next service date cannot be before service date.")

    # ------------------------------------------------------------------
    def list_records(self, *, truck_id: Optional[int] = None,
                     date_from: Optional[date] = None,
                     date_to: Optional[date] = None,
                     limit: int = 500) -> List[MaintenanceRecord]:
        session = Session()
        try:
            q = (session.query(MaintenanceRecord)
                 .options(joinedload(MaintenanceRecord.truck)))
            if truck_id:
                q = q.filter(MaintenanceRecord.truck_id == truck_id)
            if date_from:
                q = q.filter(MaintenanceRecord.service_date >= date_from)
            if date_to:
                q = q.filter(MaintenanceRecord.service_date <= date_to)
            q = q.order_by(MaintenanceRecord.service_date.desc()).limit(limit)
            records = q.all()
            for r in records:
                self._detach(r, session)
            return records
        finally:
            session.close()

    def list_due(self, *, days: int = MAINTENANCE_DUE_DAYS
                 ) -> List[MaintenanceRecord]:
        """Maintenance records whose next_service_date falls within *days*."""
        session = Session()
        try:
            today = date.today()
            horizon = today + timedelta(days=days)
            q = (session.query(MaintenanceRecord)
                 .options(joinedload(MaintenanceRecord.truck))
                 .filter(MaintenanceRecord.next_service_date.isnot(None),
                         MaintenanceRecord.next_service_date <= horizon)
                 .order_by(MaintenanceRecord.next_service_date.asc()))
            records = q.all()
            for r in records:
                self._detach(r, session)
            return records
        finally:
            session.close()

    # ------------------------------------------------------------------
    def create(self, actor, data: dict) -> MaintenanceRecord:
        require(actor, "maintenance.create")
        self._validate(data)
        session = Session()
        try:
            truck = session.query(Truck).filter_by(id=data["truck_id"]).first()
            if not truck:
                raise ValueError(f"Truck #{data['truck_id']} not found.")

            record = MaintenanceRecord(
                truck_id=data["truck_id"],
                service_type=data["service_type"],
                service_date=data["service_date"],
                next_service_date=data.get("next_service_date"),
                cost=float(data["cost"]) if data.get("cost") is not None else 0.0,
                notes=(data.get("notes") or "").strip() or None,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            self._detach(record, session)

            self.log.log_activity(
                actor.id, "maintenance_logged",
                f"Logged {record.service_type} for truck #{record.truck_id}"
            )
            return record
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update(self, actor, record_id: int, data: dict) -> MaintenanceRecord:
        require(actor, "maintenance.edit")
        self._validate(data, is_update=True)
        session = Session()
        try:
            record = session.query(MaintenanceRecord).filter_by(
                id=record_id).first()
            if not record:
                raise ValueError(f"Maintenance record #{record_id} not found.")

            updatable = {"service_type", "service_date", "next_service_date",
                         "cost", "notes"}
            for key, value in data.items():
                if key in updatable:
                    setattr(record, key, value)
            record.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(record)
            self._detach(record, session)

            self.log.log_activity(actor.id, "maintenance_updated",
                                  f"Updated maintenance #{record.id}")
            return record
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete(self, actor, record_id: int) -> bool:
        require(actor, "maintenance.delete")
        session = Session()
        try:
            record = session.query(MaintenanceRecord).filter_by(
                id=record_id).first()
            if not record:
                raise ValueError(f"Maintenance record #{record_id} not found.")
            session.delete(record)
            session.commit()
            self.log.log_activity(actor.id, "maintenance_deleted",
                                  f"Deleted maintenance #{record_id}")
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
