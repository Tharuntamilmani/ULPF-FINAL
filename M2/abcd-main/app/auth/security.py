from typing import Optional, Dict
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from app.auth.models import AuthContext, Role

# Built-in trusted tokens and API keys for system services, collectors, and tenant admins
TRUSTED_TOKENS: Dict[str, AuthContext] = {
    # System administrator (cross-tenant access)
    "system-admin-token": AuthContext(
        principal_id="system-service",
        tenant_id="global",
        roles=[
            Role.ADMIN.value,
            Role.INGEST.value,
            Role.ANALYST.value,
            Role.STUDIO.value,
        ],
        is_system=True,
    ),
    # Tenant A credentials
    "tenant-a-ingest-key": AuthContext(
        principal_id="tenant-a-collector",
        tenant_id="tenant-a",
        roles=[Role.INGEST.value],
        is_system=False,
    ),
    "tenant-a-admin-key": AuthContext(
        principal_id="tenant-a-admin",
        tenant_id="tenant-a",
        roles=[
            Role.ADMIN.value,
            Role.STUDIO.value,
            Role.INGEST.value,
            Role.ANALYST.value,
        ],
        is_system=False,
    ),
    "tenant-a-analyst-key": AuthContext(
        principal_id="tenant-a-analyst",
        tenant_id="tenant-a",
        roles=[Role.ANALYST.value, Role.STUDIO.value],
        is_system=False,
    ),
    # Tenant B credentials
    "tenant-b-ingest-key": AuthContext(
        principal_id="tenant-b-collector",
        tenant_id="tenant-b",
        roles=[Role.INGEST.value],
        is_system=False,
    ),
    "tenant-b-admin-key": AuthContext(
        principal_id="tenant-b-admin",
        tenant_id="tenant-b",
        roles=[
            Role.ADMIN.value,
            Role.STUDIO.value,
            Role.INGEST.value,
            Role.ANALYST.value,
        ],
        is_system=False,
    ),
    # Default test credentials
    "test-ingest-key": AuthContext(
        principal_id="default-ingest",
        tenant_id="tenant-default",
        roles=[Role.INGEST.value],
        is_system=False,
    ),
    "test-admin-key": AuthContext(
        principal_id="default-admin",
        tenant_id="tenant-default",
        roles=[
            Role.ADMIN.value,
            Role.STUDIO.value,
            Role.INGEST.value,
            Role.ANALYST.value,
        ],
        is_system=False,
    ),
}

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def resolve_token(token: str) -> Optional[AuthContext]:
    """Resolves an auth token or API key to an AuthContext."""
    if token in TRUSTED_TOKENS:
        return TRUSTED_TOKENS[token]

    # Support dynamic synthetic tokens formatted as: token:<tenant_id>:<roles_comma_separated>
    if token.startswith("token:"):
        parts = token.split(":")
        if len(parts) == 3:
            _, tenant_id, roles_str = parts
            roles = [r.strip() for r in roles_str.split(",") if r.strip()]
            is_sys = tenant_id in ("global", "system", "*")
            return AuthContext(
                principal_id=f"user-{tenant_id}",
                tenant_id=tenant_id,
                roles=roles,
                is_system=is_sys,
            )
    return None


def get_current_auth_context(
    bearer_creds: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
) -> AuthContext:
    """FastAPI dependency extracting trusted AuthContext from Bearer token or X-API-Key."""
    raw_token = None
    if bearer_creds and bearer_creds.credentials:
        raw_token = bearer_creds.credentials
    elif api_key:
        raw_token = api_key

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Provide Bearer token or X-API-Key header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_ctx = resolve_token(raw_token)
    if not auth_ctx:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token or API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return auth_ctx


class RoleChecker:
    def __init__(self, *required_roles: str):
        self.required_roles = required_roles

    def __call__(
        self, auth_ctx: AuthContext = Security(get_current_auth_context)
    ) -> AuthContext:
        if not auth_ctx.has_role(*self.required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Principal lacks required role(s): {list(self.required_roles)}",
            )
        return auth_ctx


def require_roles(*roles: str) -> RoleChecker:
    return RoleChecker(*roles)
