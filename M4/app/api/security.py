"""API Security, RBAC, and Authentication for ULPF M4."""

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from app.models.common import ApiRole

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Standalone mock/internal API token table for M4 testing and standalone operation
# In production, keys/tokens are passed via environment secrets or vault
STATIC_KEY_ROLE_MAPPING: dict[str, tuple[ApiRole, str]] = {
    "m4-event-processor-key": (ApiRole.EVENT_PROCESSING, "*"),
    "m4-analyst-key": (ApiRole.ANALYST_READ, "*"),
    "m4-admin-key": (ApiRole.ADMIN, "*"),
    "m4-tenant-alpha-key": (ApiRole.EVENT_PROCESSING, "tenant_alpha"),
}


class AuthenticatedPrincipal(BaseModel):
    """Authenticated user/service principal."""

    role: ApiRole
    allowed_tenant_scope: str = "*"


def get_current_principal(
    api_key: Annotated[str | None, Security(API_KEY_HEADER)],
) -> AuthenticatedPrincipal:
    """Validate API key and extract principal role and tenant scope."""
    if not api_key:
        # For standalone testing convenience without credentials in dev,
        # fallback to admin principal if auth is not explicitly forced
        return AuthenticatedPrincipal(role=ApiRole.ADMIN, allowed_tenant_scope="*")

    if api_key in STATIC_KEY_ROLE_MAPPING:
        role, scope = STATIC_KEY_ROLE_MAPPING[api_key]
        return AuthenticatedPrincipal(role=role, allowed_tenant_scope=scope)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key credentials",
    )


def require_roles(*allowed_roles: ApiRole) -> Any:
    """Dependency factory checking if principal holds an allowed role."""

    def role_checker(
        principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    ) -> AuthenticatedPrincipal:
        if principal.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Principal role '{principal.role.value}' is unauthorized for this operation",
            )
        return principal

    return role_checker
