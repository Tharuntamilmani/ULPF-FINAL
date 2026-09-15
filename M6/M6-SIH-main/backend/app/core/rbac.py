"""
RBAC helper — role-based and tenant-aware permission checks.
Establishes:
    SUPER_ADMIN (ADMINISTRATOR as exact alias)
    TENANT_ADMIN
    PARSER_DEVELOPER
    SECURITY_ANALYST
    VIEWER
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, status

from backend.app.core.dependencies import dep_current_user

SUPER_ADMIN = "SUPER_ADMIN"
ADMIN = "ADMINISTRATOR"  # Backward compatibility: exact alias of SUPER_ADMIN
TENANT_ADMIN = "TENANT_ADMIN"
PARSER_DEV = "PARSER_DEVELOPER"
SEC_ANALYST = "SECURITY_ANALYST"
VIEWER = "VIEWER"

# All valid role names
ALL_ROLES = {SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER}


def normalize_roles(roles: tuple[str, ...] | list[str] | set[str]) -> set[str]:
    """Ensure SUPER_ADMIN and ADMINISTRATOR are treated as exact aliases."""
    normalized = set(roles)
    if SUPER_ADMIN in normalized or ADMIN in normalized:
        normalized.add(SUPER_ADMIN)
        normalized.add(ADMIN)
    return normalized


def require_roles(*roles: str) -> Callable[..., Any]:
    """
    FastAPI dependency factory.
    Raises 403 if the current user does not hold at least one of the given roles.
    SUPER_ADMIN and ADMINISTRATOR are exact aliases.
    """
    allowed_roles = normalize_roles(roles)

    async def checker(
        current_user: Any = Depends(dep_current_user),
    ) -> Any:
        if getattr(current_user, "is_super_admin", False) or getattr(
            current_user, "is_superuser", False
        ):
            return current_user

        user_roles = normalize_roles(getattr(current_user, "role_names", []))
        if not user_roles.intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Operation requires one of: {list(allowed_roles)}. "
                    f"Your roles: {list(user_roles)}"
                ),
            )
        return current_user

    return checker


def get_primary_role(user: Any) -> str:
    """Return the highest-privilege role the user holds."""
    user_roles = normalize_roles(getattr(user, "role_names", []))
    priority = [SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER]
    for role in priority:
        if role in user_roles:
            return role
    return VIEWER
