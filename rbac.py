"""Explicit role permissions and resource-scoped authorization for Raptor."""
from __future__ import annotations

PERMISSIONS = {
    "admin": {
        "users.view_all": True, "users.create": True, "users.update_role": True, "users.delete": True,
        "teams.view_all": "all", "teams.create": True, "teams.update": "all", "teams.delete": True, "teams.assign_coaches": True,
        "roster.view": "all", "roster.create": "all", "roster.update": "all", "roster.delete": True,
        "performance.view_all": "all", "performance.create": "all", "performance.update": "all", "performance.delete": True,
        "matches.view_all": "all", "matches.create": True, "matches.update": "all", "matches.delete": True,
        "financial.view": "all", "financial.create": True, "financial.update": "all", "financial.delete": True,
        "reports.view": "all", "analytics.view": "all", "admin.access": True, "system.configure": True,
    },
    "manager": {
        "users.view_all": False, "users.create": False, "users.update_role": False, "users.delete": False,
        "teams.view_all": "all", "teams.create": True, "teams.update": "all", "teams.delete": False, "teams.assign_coaches": True,
        "roster.view": "all", "roster.create": "all", "roster.update": "all", "roster.delete": "all",
        "performance.view_all": "all", "performance.create": True, "performance.update": "all", "performance.delete": False,
        "matches.view_all": "all", "matches.create": True, "matches.update": "all", "matches.delete": False,
        "financial.view": "all", "financial.create": True, "financial.update": "all", "financial.delete": False,
        "reports.view": "all", "analytics.view": "all", "admin.access": False, "system.configure": False,
    },
    "coach": {
        "users.view_all": False, "users.create": False, "users.update_role": False, "users.delete": False,
        "teams.view_all": "assigned", "teams.create": False, "teams.update": "assigned", "teams.delete": False, "teams.assign_coaches": False,
        "roster.view": "assigned", "roster.create": "assigned", "roster.update": False, "roster.delete": "assigned",
        "performance.view_all": "assigned", "performance.create": "assigned", "performance.update": "assigned", "performance.delete": False,
        "matches.view_all": "assigned", "matches.create": False, "matches.update": False, "matches.delete": False,
        "financial.view": False, "financial.create": False, "financial.update": False, "financial.delete": False,
        "reports.view": "assigned", "analytics.view": "assigned", "admin.access": False, "system.configure": False,
    },
    "analyst": {
        "users.view_all": False, "users.create": False, "users.update_role": False, "users.delete": False,
        "teams.view_all": "assigned", "teams.create": False, "teams.update": False, "teams.delete": False, "teams.assign_coaches": False,
        "roster.view": "assigned", "roster.create": "assigned", "roster.update": False, "roster.delete": "assigned",
        "performance.view_all": "assigned", "performance.create": False, "performance.update": False, "performance.delete": False,
        "matches.view_all": "assigned", "matches.create": False, "matches.update": False, "matches.delete": False,
        "financial.view": False, "financial.create": False, "financial.update": False, "financial.delete": False,
        "reports.view": "assigned", "analytics.view": "assigned", "admin.access": False, "system.configure": False,
    },
    "player": {
        "users.view_all": False, "users.create": False, "users.update_role": False, "users.delete": False,
        "teams.view_all": "own", "teams.create": False, "teams.update": False, "teams.delete": False, "teams.assign_coaches": False,
        "roster.view": "own", "roster.create": False, "roster.update": False, "roster.delete": False,
        "performance.view_all": "own", "performance.create": "own", "performance.update": False, "performance.delete": False,
        "matches.view_all": "own", "matches.create": False, "matches.update": False, "matches.delete": False,
        "financial.view": False, "financial.create": False, "financial.update": False, "financial.delete": False,
        "reports.view": "own", "analytics.view": "own", "admin.access": False, "system.configure": False,
    },
}

_DISPLAY = {
    "admin": ("Admin", "Full access to users, modules, system settings, and operations."),
    "manager": ("Manager", "Manages teams, rosters, competition operations, and permitted finances."),
    "coach": ("Coach", "Manages assigned team performance and sees assigned team information."),
    "analyst": ("Analyst", "Reads authorized team performance, scrim results, and analytics."),
    "player": ("Player", "Sees own profile, records, reports, and permitted team information."),
}
_LEVELS = {"admin": 100, "manager": 80, "coach": 70, "analyst": 60, "player": 50}
ROLES = {role: {"level": _LEVELS[role], "display_name": _DISPLAY[role][0], "description": _DISPLAY[role][1], "permissions": permissions} for role, permissions in PERMISSIONS.items()}


def has_permission(role: str | None, permission: str) -> bool:
    """Check an operation explicitly; levels never imply permissions."""
    permissions = PERMISSIONS.get(role or "")
    return bool(permissions and permission in permissions and permissions[permission] not in (False, None))


def can_assign_team_role(role: str | None, target_role: str | None) -> bool:
    """Managers can assign coaches; Admin can assign coaches and analysts."""
    return ((role == "admin" and target_role in {"coach", "analyst"})
            or (role == "manager" and target_role == "coach"))


def permission_scope(role: str | None, permission: str):
    permissions = PERMISSIONS.get(role or "") or {}
    return permissions.get(permission, False)


def resource_allowed(role: str | None, permission: str, *, team_id=None, player_id=None,
                     assigned_team_ids=(), own_team_id=None, own_player_id=None) -> bool:
    scope = permission_scope(role, permission)
    if scope is True or scope == "all":
        return True
    if scope == "assigned":
        return team_id is not None and team_id in set(assigned_team_ids or ())
    if scope == "own":
        if player_id is not None:
            return own_player_id is not None and player_id == own_player_id
        return team_id is not None and own_team_id is not None and team_id == own_team_id
    return False
