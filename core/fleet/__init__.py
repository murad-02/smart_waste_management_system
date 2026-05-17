"""Fleet & Truck Management subsystem.

A self-contained operational module covering trucks, drivers, routes,
collection trips, and maintenance. The package intentionally has no
dependency on the computer-vision detection engine so the application
can run with or without CV capabilities.
"""

from core.fleet.truck_service import TruckService
from core.fleet.driver_service import DriverService
from core.fleet.route_service import RouteService
from core.fleet.trip_service import TripService
from core.fleet.maintenance_service import MaintenanceService
from core.fleet.fleet_analytics import FleetAnalytics
from core.fleet.fleet_permissions import can, ACTIONS

__all__ = [
    "TruckService",
    "DriverService",
    "RouteService",
    "TripService",
    "MaintenanceService",
    "FleetAnalytics",
    "can",
    "ACTIONS",
]
