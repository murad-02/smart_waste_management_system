"""Route CRUD service."""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import or_

from database.db_setup import Session
from database.fleet_models import Route
from core.log_manager import LogManager
from core.fleet.constants import ROUTE_STATUSES
from core.fleet.fleet_permissions import require

logger = logging.getLogger(__name__)


class RouteService:
    def __init__(self):
        self.log = LogManager()

    @staticmethod
    def _detach(route: Route, session) -> Route:
        _ = (route.id, route.route_name, route.zone,
             route.estimated_distance, route.estimated_duration,
             route.status, route.notes, route.is_active,
             route.created_at, route.updated_at)
        session.expunge(route)
        return route

    @staticmethod
    def _validate(data: dict, *, is_update: bool = False):
        if not is_update or "route_name" in data:
            if not (data.get("route_name") or "").strip():
                raise ValueError("Route name is required.")
        if not is_update or "zone" in data:
            if not (data.get("zone") or "").strip():
                raise ValueError("Zone is required.")
        if data.get("estimated_distance") is not None:
            try:
                if float(data["estimated_distance"]) < 0:
                    raise ValueError("Distance cannot be negative.")
            except (TypeError, ValueError):
                raise ValueError("Estimated distance must be a number.")
        if data.get("estimated_duration") is not None:
            try:
                if int(data["estimated_duration"]) < 0:
                    raise ValueError("Duration cannot be negative.")
            except (TypeError, ValueError):
                raise ValueError("Estimated duration must be an integer (minutes).")
        if "status" in data and data["status"] not in ROUTE_STATUSES:
            raise ValueError(f"Invalid route status: {data['status']!r}.")

    # ------------------------------------------------------------------
    def list_routes(self, *, search: str = "", zone: Optional[str] = None,
                    status: Optional[str] = None,
                    include_inactive: bool = False) -> List[Route]:
        session = Session()
        try:
            q = session.query(Route)
            if not include_inactive:
                q = q.filter(Route.is_active.is_(True))
            if zone:
                q = q.filter(Route.zone == zone)
            if status:
                q = q.filter(Route.status == status)
            if search:
                like = f"%{search.strip()}%"
                q = q.filter(or_(
                    Route.route_name.ilike(like),
                    Route.zone.ilike(like),
                ))
            q = q.order_by(Route.route_name.asc())
            routes = q.all()
            for r in routes:
                self._detach(r, session)
            return routes
        finally:
            session.close()

    def get(self, route_id: int) -> Optional[Route]:
        session = Session()
        try:
            route = session.query(Route).filter_by(id=route_id).first()
            return self._detach(route, session) if route else None
        finally:
            session.close()

    # ------------------------------------------------------------------
    def create(self, actor, data: dict) -> Route:
        require(actor, "route.create")
        self._validate(data)
        session = Session()
        try:
            existing = session.query(Route).filter_by(
                route_name=data["route_name"].strip()
            ).first()
            if existing:
                raise ValueError(f"Route '{data['route_name']}' already exists.")

            route = Route(
                route_name=data["route_name"].strip(),
                zone=data["zone"].strip(),
                estimated_distance=(float(data["estimated_distance"])
                                    if data.get("estimated_distance") is not None
                                    else None),
                estimated_duration=(int(data["estimated_duration"])
                                    if data.get("estimated_duration") is not None
                                    else None),
                status=data.get("status") or "active",
                notes=(data.get("notes") or "").strip() or None,
            )
            session.add(route)
            session.commit()
            session.refresh(route)
            self._detach(route, session)

            self.log.log_activity(actor.id, "route_created",
                                  f"Created route '{route.route_name}' (zone {route.zone})")
            return route
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update(self, actor, route_id: int, data: dict) -> Route:
        require(actor, "route.edit")
        self._validate(data, is_update=True)
        session = Session()
        try:
            route = session.query(Route).filter_by(id=route_id).first()
            if not route:
                raise ValueError(f"Route #{route_id} not found.")

            updatable = {"route_name", "zone", "estimated_distance",
                         "estimated_duration", "status", "notes"}
            for key, value in data.items():
                if key in updatable:
                    if isinstance(value, str):
                        value = value.strip() or None
                    setattr(route, key, value)
            route.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(route)
            self._detach(route, session)

            self.log.log_activity(actor.id, "route_updated",
                                  f"Updated route '{route.route_name}'")
            return route
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def soft_delete(self, actor, route_id: int) -> bool:
        require(actor, "route.delete")
        session = Session()
        try:
            route = session.query(Route).filter_by(id=route_id).first()
            if not route:
                raise ValueError(f"Route #{route_id} not found.")
            route.is_active = False
            route.status = "inactive"
            session.commit()
            self.log.log_activity(actor.id, "route_deactivated",
                                  f"Deactivated route '{route.route_name}'")
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
