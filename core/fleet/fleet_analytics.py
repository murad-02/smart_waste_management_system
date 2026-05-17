"""Aggregate queries powering the Fleet dashboard and reports.

Each method returns plain dicts / lists so the UI is free to render with
matplotlib, tables, or anywhere else.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple

from sqlalchemy import func

from database.db_setup import Session
from database.fleet_models import (
    Truck, Driver, Route, CollectionTrip, MaintenanceRecord
)
from core.fleet.constants import (
    TRUCK_STATUSES, TRIP_STATUSES, MAINTENANCE_DUE_DAYS
)

logger = logging.getLogger(__name__)


class FleetAnalytics:
    """Read-only aggregations for dashboards & reports."""

    # ------------------------------------------------------------------
    # Truck summary
    # ------------------------------------------------------------------
    def truck_status_counts(self) -> Dict[str, int]:
        session = Session()
        try:
            rows = (session.query(Truck.status, func.count(Truck.id))
                    .filter(Truck.is_active.is_(True))
                    .group_by(Truck.status).all())
            counts = {s: 0 for s in TRUCK_STATUSES}
            for status, count in rows:
                counts[status] = count
            counts["active"] = counts.get("available", 0) + counts.get("on_route", 0)
            counts["total"] = sum(c for s, c in counts.items()
                                  if s in TRUCK_STATUSES)
            return counts
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Trip metrics
    # ------------------------------------------------------------------
    def trip_counts_today(self) -> Dict[str, int]:
        session = Session()
        try:
            start = datetime.combine(date.today(), datetime.min.time())
            end = start + timedelta(days=1)
            rows = (session.query(CollectionTrip.trip_status,
                                  func.count(CollectionTrip.id))
                    .filter(CollectionTrip.created_at >= start,
                            CollectionTrip.created_at < end)
                    .group_by(CollectionTrip.trip_status).all())
            counts = {s: 0 for s in TRIP_STATUSES}
            for status, count in rows:
                counts[status] = count
            counts["total"] = sum(counts.values())
            return counts

        finally:
            session.close()

    def trips_per_day(self, days: int = 7) -> Tuple[List[str], List[int]]:
        """Return (labels, counts) of trips for the last *days* days."""
        session = Session()
        try:
            today = date.today()
            labels = [(today - timedelta(days=i)).strftime("%a %d")
                      for i in range(days - 1, -1, -1)]
            buckets = {(today - timedelta(days=i)): 0
                       for i in range(days - 1, -1, -1)}

            start = datetime.combine(today - timedelta(days=days - 1),
                                     datetime.min.time())
            rows = (session.query(CollectionTrip.created_at)
                    .filter(CollectionTrip.created_at >= start)
                    .all())
            for (created_at,) in rows:
                day = created_at.date()
                if day in buckets:
                    buckets[day] += 1
            counts = [buckets[today - timedelta(days=i)]
                      for i in range(days - 1, -1, -1)]
            return labels, counts
        finally:
            session.close()

    def truck_utilization(self, days: int = 30) -> List[Dict]:
        """For each active truck, return percentage of days it ran a trip.

        Returned shape:
            [{"truck_code": ..., "trips": N, "utilization_pct": 0..100}, ...]
        """
        session = Session()
        try:
            since = datetime.combine(date.today() - timedelta(days=days - 1),
                                     datetime.min.time())
            trucks = (session.query(Truck)
                      .filter(Truck.is_active.is_(True))
                      .order_by(Truck.truck_code).all())

            trip_rows = (session.query(CollectionTrip.truck_id,
                                       CollectionTrip.created_at)
                         .filter(CollectionTrip.created_at >= since)
                         .all())
            by_truck: Dict[int, set] = {}
            counts_by_truck: Dict[int, int] = {}
            for tid, created_at in trip_rows:
                counts_by_truck[tid] = counts_by_truck.get(tid, 0) + 1
                by_truck.setdefault(tid, set()).add(created_at.date())

            result = []
            for t in trucks:
                active_days = len(by_truck.get(t.id, set()))
                util = (active_days / days) * 100.0 if days else 0.0
                result.append({
                    "truck_code": t.truck_code,
                    "trips": counts_by_truck.get(t.id, 0),
                    "utilization_pct": round(util, 1),
                })
            return result
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Maintenance metrics
    # ------------------------------------------------------------------
    def maintenance_due_count(self, days: int = MAINTENANCE_DUE_DAYS) -> int:
        session = Session()
        try:
            horizon = date.today() + timedelta(days=days)
            return (session.query(func.count(MaintenanceRecord.id))
                    .filter(MaintenanceRecord.next_service_date.isnot(None),
                            MaintenanceRecord.next_service_date <= horizon)
                    .scalar()) or 0
        finally:
            session.close()

    def maintenance_cost_summary(self, days: int = 90) -> Dict[str, float]:
        """Total + monthly trend for the last *days* days."""
        session = Session()
        try:
            since = date.today() - timedelta(days=days)
            total = (session.query(func.coalesce(
                        func.sum(MaintenanceRecord.cost), 0.0))
                     .filter(MaintenanceRecord.service_date >= since)
                     .scalar()) or 0.0
            count = (session.query(func.count(MaintenanceRecord.id))
                     .filter(MaintenanceRecord.service_date >= since)
                     .scalar()) or 0
            avg = (total / count) if count else 0.0
            return {"total_cost": float(total),
                    "records": int(count),
                    "avg_cost": float(avg)}
        finally:
            session.close()

    def maintenance_trend(self, days: int = 30) -> Tuple[List[str], List[float]]:
        """Daily maintenance cost over the last *days* days."""
        session = Session()
        try:
            today = date.today()
            buckets = {(today - timedelta(days=i)): 0.0
                       for i in range(days - 1, -1, -1)}
            since = today - timedelta(days=days - 1)
            rows = (session.query(MaintenanceRecord.service_date,
                                  MaintenanceRecord.cost)
                    .filter(MaintenanceRecord.service_date >= since)
                    .all())
            for d, cost in rows:
                if d in buckets:
                    buckets[d] += float(cost or 0.0)
            labels = [(today - timedelta(days=i)).strftime("%d %b")
                      for i in range(days - 1, -1, -1)]
            values = [buckets[today - timedelta(days=i)]
                      for i in range(days - 1, -1, -1)]
            return labels, values
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Drivers & routes
    # ------------------------------------------------------------------
    def driver_count(self) -> int:
        session = Session()
        try:
            return session.query(func.count(Driver.id)).filter(
                Driver.is_active.is_(True)).scalar() or 0
        finally:
            session.close()

    def route_count(self) -> int:
        session = Session()
        try:
            return session.query(func.count(Route.id)).filter(
                Route.is_active.is_(True)).scalar() or 0
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Aggregated summary (one call → all KPI values)
    # ------------------------------------------------------------------
    def summary(self) -> Dict:
        truck_counts = self.truck_status_counts()
        trip_today = self.trip_counts_today()
        cost = self.maintenance_cost_summary()
        return {
            "trucks_total":      truck_counts.get("total", 0),
            "trucks_active":     truck_counts.get("active", 0),
            "trucks_maintenance": truck_counts.get("maintenance", 0),
            "drivers_active":    self.driver_count(),
            "routes_active":     self.route_count(),
            "trips_today":       trip_today.get("total", 0),
            "trips_completed_today": trip_today.get("completed", 0),
            "maintenance_due":   self.maintenance_due_count(),
            "maintenance_cost_90d": cost["total_cost"],
        }
