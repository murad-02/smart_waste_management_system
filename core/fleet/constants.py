"""Shared constants for the Fleet module.

Keeping statuses centralised avoids divergent string literals scattered
across services and screens.
"""

# --- Truck ---------------------------------------------------------------
TRUCK_STATUSES = [
    "available",
    "on_route",
    "maintenance",
    "out_of_service",
    "inactive",
]

FUEL_TYPES = ["diesel", "petrol", "cng", "lng", "electric", "hybrid"]

# --- Driver --------------------------------------------------------------
DRIVER_STATUSES = ["available", "on_duty", "off_duty", "suspended"]

# --- Route ---------------------------------------------------------------
ROUTE_STATUSES = ["active", "inactive", "draft"]

# --- Trip ----------------------------------------------------------------
TRIP_STATUSES = ["scheduled", "active", "completed", "cancelled"]

# --- Maintenance ---------------------------------------------------------
SERVICE_TYPES = [
    "oil_change",
    "tire_rotation",
    "brake_service",
    "engine_repair",
    "transmission",
    "inspection",
    "general_service",
    "other",
]

# Treat maintenance as "due soon" when next_service_date is within this many days.
MAINTENANCE_DUE_DAYS = 14


def pretty(value: str) -> str:
    """Human-readable label for a snake_case status."""
    return (value or "").replace("_", " ").title()
