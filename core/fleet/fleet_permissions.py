"""Role-based access control helper for the Fleet subsystem.

A single source of truth used by:
  * the sidebar (to hide menu items)
  * each screen (to disable / hide action buttons)
  * each service (to defensively reject unauthorised writes)
"""

# Action identifiers
ACTIONS = {
    # Trucks
    "truck.view":        ["admin", "supervisor", "operator"],
    "truck.create":      ["admin"],
    "truck.edit":        ["admin"],
    "truck.delete":      ["admin"],

    # Drivers
    "driver.view":       ["admin", "supervisor"],
    "driver.create":     ["admin"],
    "driver.edit":       ["admin", "supervisor"],
    "driver.delete":     ["admin"],

    # Routes
    "route.view":        ["admin", "supervisor", "operator"],
    "route.create":      ["admin", "supervisor"],
    "route.edit":        ["admin", "supervisor"],
    "route.delete":      ["admin"],

    # Trips
    "trip.view":         ["admin", "supervisor", "operator"],   # operator: own only
    "trip.create":       ["admin", "supervisor"],
    "trip.edit":         ["admin", "supervisor"],
    "trip.update_own":   ["admin", "supervisor", "operator"],
    "trip.delete":       ["admin"],

    # Maintenance
    "maintenance.view":   ["admin", "supervisor"],
    "maintenance.create": ["admin", "supervisor"],
    "maintenance.edit":   ["admin", "supervisor"],
    "maintenance.delete": ["admin"],

    # Dashboard / reports
    "fleet.dashboard":    ["admin", "supervisor", "operator"],
    "fleet.reports":      ["admin", "supervisor"],
}


def can(user, action: str) -> bool:
    """Return True when *user* has permission for *action*."""
    if user is None or not getattr(user, "role", None):
        return False
    allowed_roles = ACTIONS.get(action, [])
    return user.role in allowed_roles


def require(user, action: str):
    """Raise PermissionError when *user* lacks *action*."""
    if not can(user, action):
        raise PermissionError(
            f"User '{getattr(user, 'username', '?')}' lacks permission for '{action}'."
        )
