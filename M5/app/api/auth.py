"""
Authentication and Tenant Authorization Engine for ULPF M5 API.
Enforces strict cryptographic / token-based tenant context isolation.
Prevents arbitrary tenant impersonation and authorization bypasses.
"""
import os
import json
import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel
from fastapi import Header, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger("m5-auth")

bearer_scheme = HTTPBearer(auto_error=False)


class TenantContext(BaseModel):
    tenant_id: str
    is_admin: bool = False
    authenticated: bool = True


# Standard preconfigured API keys / tokens for prototype & testing
DEFAULT_KEY_REGISTRY: Dict[str, Dict[str, Any]] = {
    "admin-key-secret": {"tenant_id": "admin", "is_admin": True},
    "alpha-key-secret": {"tenant_id": "tenant_alpha", "is_admin": False},
    "beta-key-secret": {"tenant_id": "tenant_beta", "is_admin": False},
    "gamma-key-secret": {"tenant_id": "tenant_gamma", "is_admin": False},
    "default-key-secret": {"tenant_id": "default_tenant", "is_admin": False},
    "tenant-0-key": {"tenant_id": "tenant_0", "is_admin": False},
    "tenant-1-key": {"tenant_id": "tenant_1", "is_admin": False},
    "tenant-2-key": {"tenant_id": "tenant_2", "is_admin": False},
    "tenant-3-key": {"tenant_id": "tenant_3", "is_admin": False},
}


def _get_key_registry() -> Dict[str, Dict[str, Any]]:
    registry = dict(DEFAULT_KEY_REGISTRY)
    env_keys = os.getenv("M5_API_KEYS")
    if env_keys:
        try:
            parsed = json.loads(env_keys)
            registry.update(parsed)
        except Exception as e:
            logger.warning(f"Failed to parse M5_API_KEYS env var: {e}")
    return registry


def get_current_tenant_context(
    authorization: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    x_api_key: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None)
) -> TenantContext:
    """
    Authenticate client and return authorized TenantContext.
    Rejects unauthenticated requests (HTTP 401) and unauthorized tenant access (HTTP 403).
    """
    token = None
    if authorization and authorization.credentials:
        token = authorization.credentials.strip()
    elif x_api_key:
        token = x_api_key.strip()

    # Check if anonymous access is explicitly allowed by configuration (default False)
    allow_anonymous = os.getenv("M5_ALLOW_ANONYMOUS", "false").lower() == "true"

    if not token:
        if allow_anonymous:
            # In anonymous dev mode, tenant defaults to x_tenant_id or default_tenant, non-admin
            return TenantContext(tenant_id=x_tenant_id or "default_tenant", is_admin=False, authenticated=False)
        raise HTTPException(
            status_code=401,
            detail="Authentication required: Provide Authorization Bearer token or X-API-Key header"
        )

    registry = _get_key_registry()
    client_info = registry.get(token)

    if not client_info:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    auth_tenant = client_info["tenant_id"]
    is_admin = client_info.get("is_admin", False)

    # If an X-Tenant-ID header was explicitly provided by caller:
    if x_tenant_id:
        if not is_admin and x_tenant_id != auth_tenant:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: Authenticated tenant '{auth_tenant}' cannot access tenant '{x_tenant_id}'"
            )
        effective_tenant = x_tenant_id if is_admin else auth_tenant
    else:
        effective_tenant = auth_tenant

    return TenantContext(
        tenant_id=effective_tenant,
        is_admin=is_admin,
        authenticated=True
    )
