"""Collection-trip orchestration.

A trip is the operational entity that ties truck + driver + route together
and carries timing, waste-weight, and lifecycle state.
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Optional

from sqlalchemy.orm import joinedload

from database.db_setup import Session
from database.fleet_models import (
    CollectionTrip, Truck, Driver, Route
)
from core.log_manager import LogManager
from core.fleet.constants import TRIP_STATUSES
from core.fleet.fleet_permissions import require, can

logger = logging.getLogger(__name__)


class TripService:
    def __init__(self):
        self.log = LogManager()

    # ------------------------------------------------------------------
    @staticmethod
    def _detach(trip: CollectionTrip, session) -> CollectionTrip:
        _ = (trip.id, trip.truck_id, trip.driver_id, trip.route_id,
             trip.start_time, trip.end_time, trip.waste_weight,
             trip.trip_status, trip.notes,
             trip.created_by, trip.created_at, trip.updated_at)
        if trip.truck:
            _ = (trip.truck.id, trip.truck.truck_code, trip.truck.plate_number)
        if trip.driver:
            _ = (trip.driver.id, trip.driver.name)
        if trip.route:
            _ = (trip.route.id, trip.route.route_name, trip.route.zone)
        session.expunge(trip)
        return trip

    @staticmethod
    def _validate(data: dict, *, is_update: bool = False):
        if not is_update:
            for field in ("truck_id", "driver_id", "route_id"):
                if not data.get(field):
                    raise ValueError(f"{field.replace('_', ' ').title()} is required.")
        if "trip_status" in data and data["trip_status"] not in TRIP_STATUSES:
            raise ValueError(f"Invalid trip status: {data['trip_status']!r}.")
        if data.get("waste_weight") is not None:
            try:
                if float(data["waste_weight"]) < 0:
                    raise ValueError("Waste weight cannot be negative.")
            except (TypeError, ValueError):
                raise ValueError("Waste weight must be a number.")
        if data.get("start_time") and data.get("end_time"):
            if data["end_time"] < data["start_time"]:
                raise ValueError("End time cannot be before start time.")

    # ------------------------------------------------------------------
    def list_trips(self, *, actor=None, status: Optional[str] = None,
                   truck_id: Optional[int] = None,
                   driver_id: Optional[int] = None,
                   route_id: Optional[int] = None,
                   date_from: Optional[date] = None,
                   date_to: Optional[date] = None,
                   limit: int = 500) -> List[CollectionTrip]:
        """List trips with optional filters.

        Operators only see trips they created (i.e. assigned to them via
        ``created_by``); admins and supervisors see everything.
        """
        session = Session()
        try:
            q = (session.query(CollectionTrip)
                 .options(joinedload(CollectionTrip.truck),
                          joinedload(CollectionTrip.driver),
                          joinedload(CollectionTrip.route)))

            if actor is not None and actor.role == "operator":
                q = q.filter(CollectionTrip.created_by == actor.id)

            if status:
                q = q.filter(CollectionTrip.trip_status == status)
            if truck_id:
                q = q.filter(CollectionTrip.truck_id == truck_id)
            if driver_id:
                q = q.filter(CollectionTrip.driver_id == driver_id)
            if route_id:
                q = q.filter(CollectionTrip.route_id == route_id)
            if date_from:
                q = q.filter(CollectionTrip.created_at >= datetime.combine(
                    date_from, datetime.min.time()))
            if date_to:
                q = q.filter(CollectionTrip.created_at <= datetime.combine(
                    date_to, datetime.max.time()))

            q = q.order_by(CollectionTrip.created_at.desc()).limit(limit)
            trips = q.all()
            for t in trips:
                self._detach(t, session)
            return trips
        finally:
            session.close()

    def get(self, trip_id: int) -> Optional[CollectionTrip]:
        session = Session()
        try:
            trip = (session.query(CollectionTrip)
                    .options(joinedload(CollectionTrip.truck),
                             joinedload(CollectionTrip.driver),
                             joinedload(CollectionTrip.route))
                    .filter_by(id=trip_id).first())
            return self._detach(trip, session) if trip else None
        finally:
            session.close()

    # ------------------------------------------------------------------
    def create(self, actor, data: dict) -> CollectionTrip:
        require(actor, "trip.create")
        self._validate(data)
        session = Session()
        try:
            self._verify_refs(session, data)

            trip = CollectionTrip(
                truck_id=data["truck_id"],
                driver_id=data["driver_id"],
                route_id=data["route_id"],
                start_time=data.get("start_time"),
                end_time=data.get("end_time"),
                waste_weight=(float(data["waste_weight"])
                              if data.get("waste_weight") is not None else 0.0),
                trip_status=data.get("trip_status") or "scheduled",
                notes=(data.get("notes") or "").strip() or None,
                created_by=actor.id,
            )
            session.add(trip)
            session.commit()
            session.refresh(trip)
            self._detach(trip, session)

            self.log.log_activity(
                actor.id, "trip_created",
                f"Scheduled trip #{trip.id} (truck {trip.truck_id}, "
                f"driver {trip.driver_id}, route {trip.route_id})"
            )
            return trip
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update(self, actor, trip_id: int, data: dict) -> CollectionTrip:
        # Operators can update only their own trips and only certain fields.
        is_full_edit = can(actor, "trip.edit")
        if not is_full_edit:
            require(actor, "trip.update_own")
        self._validate(data, is_update=True)

        session = Session()
        try:
            trip = session.query(CollectionTrip).filter_by(id=trip_id).first()
            if not trip:
                raise ValueError(f"Trip #{trip_id} not found.")

            if not is_full_edit and trip.created_by != actor.id:
                raise PermissionError("You can only update trips assigned to you.")

            if not is_full_edit:
                # Operator may only progress status / record telemetry.
                operator_fields = {"trip_status", "start_time", "end_time",
                                   "waste_weight", "notes"}
                data = {k: v for k, v in data.items() if k in operator_fields}

            if any(k in data for k in ("truck_id", "driver_id", "route_id")):
                self._verify_refs(session, {
                    "truck_id": data.get("truck_id") or trip.truck_id,
                    "driver_id": data.get("driver_id") or trip.driver_id,
                    "route_id": data.get("route_id") or trip.route_id,
                })

            updatable = {"truck_id", "driver_id", "route_id",
                         "start_time", "end_time", "waste_weight",
                         "trip_status", "notes"}
            for key, value in data.items():
                if key in updatable:
                    setattr(trip, key, value)
            trip.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(trip)
            self._detach(trip, session)

            self.log.log_activity(actor.id, "trip_updated",
                                  f"Updated trip #{trip.id} ({trip.trip_status})")
            return trip
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def set_status(self, actor, trip_id: int, new_status: str) -> CollectionTrip:
        """Convenience: progress a trip's lifecycle."""
        if new_status not in TRIP_STATUSES:
            raise ValueError(f"Invalid trip status: {new_status!r}.")
        data = {"trip_status": new_status}
        if new_status == "active":
            data["start_time"] = datetime.utcnow()
        elif new_status == "completed":
            data["end_time"] = datetime.utcnow()
        return self.update(actor, trip_id, data)

    def delete(self, actor, trip_id: int) -> bool:
        require(actor, "trip.delete")
        session = Session()
        try:
            trip = session.query(CollectionTrip).filter_by(id=trip_id).first()
            if not trip:
                raise ValueError(f"Trip #{trip_id} not found.")
            session.delete(trip)
            session.commit()
            self.log.log_activity(actor.id, "trip_deleted",
                                  f"Deleted trip #{trip_id}")
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ------------------------------------------------------------------
    @staticmethod
    def _verify_refs(session, data: dict):
        truck = session.query(Truck).filter_by(
            id=data["truck_id"], is_active=True).first()
        if not truck:
            raise ValueError(f"Truck #{data['truck_id']} is not available.")
        driver = session.query(Driver).filter_by(
            id=data["driver_id"], is_active=True).first()
        if not driver:
            raise ValueError(f"Driver #{data['driver_id']} is not available.")
        route = session.query(Route).filter_by(
            id=data["route_id"], is_active=True).first()
        if not route:
            raise ValueError(f"Route #{data['route_id']} is not available.")

    # ------------------------------------------------------------------
    # Dashboard helpers
    # ------------------------------------------------------------------
    def count_today(self) -> dict:
        """Return today's scheduled, active, completed counts."""
        session = Session()
        try:
            start = datetime.combine(date.today(), datetime.min.time())
            end = start + timedelta(days=1)
            counts = {s: 0 for s in TRIP_STATUSES}
            rows = (session.query(CollectionTrip.trip_status,
                                  CollectionTrip.id)
                    .filter(CollectionTrip.created_at >= start,
                            CollectionTrip.created_at < end)
                    .all())
            for status, _ in rows:
                counts[status] = counts.get(status, 0) + 1
            counts["total"] = sum(counts.values())
            return counts
        finally:
            session.close()
