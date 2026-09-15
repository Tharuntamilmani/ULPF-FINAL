"""
Centralized tenant context.
Resolves effective tenant ID and enforces server-side tenant boundaries.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Query, status

from backend.app.core.dependencies import DepDB, dep_current_user
from backend.app.models.tenant import TenantStatus
from backend.app.models.user import User
from backend.app.repositories.tenant_repo import TenantRepository


class TenantContext:
    def __init__(
        self,
        user: User,
        effective_tenant_id: str | None,
        is_super_admin: bool,
    ) -> None:
        self.user = user
        self.tenant_id = effective_tenant_id
        self.is_super_admin = is_super_admin

    def require_tenant_id(self) -> str:
        """For tenant-owned resource creation/mutation, tenant_id must be resolved."""
        if not self.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant context required for this operation.",
            )
        return self.tenant_id


async def dep_tenant_context(
    current_user: Annotated[Any, Depends(dep_current_user)],
    db: DepDB,
    tenant_id: str | None = Query(None, description="Optional tenant ID (SUPER_ADMIN only)"),
) -> TenantContext:
    """
    Centralized dependency resolving effective tenant context.
    Rules:
    - If user is SUPER_ADMIN:
        - can operate with explicit ?tenant_id=... or platform-wide (None)
        - if explicit tenant_id provided, verifies tenant exists
    - If user is tenant-scoped:
        - authenticated user MUST have tenant_id
        - user's tenant MUST be ACTIVE (not SUSPENDED/DISABLED)
        - client MUST NOT send a different ?tenant_id= query param; if sent, HTTP 403 Forbidden!
        - effective tenant is always current_user.tenant_id
    """
    is_super = getattr(current_user, "is_super_admin", False)

    if is_super:
        if tenant_id:
            tenant_repo = TenantRepository(db)
            tenant = await tenant_repo.get(tenant_id)
            if not tenant:
                tenant = await tenant_repo.get_by_slug(tenant_id)
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant '{tenant_id}' not found",
                )
            return TenantContext(current_user, tenant.id, is_super_admin=True)
        default_tid = getattr(current_user, "tenant_id", None)
        return TenantContext(current_user, default_tid, is_super_admin=True)

    # Tenant-scoped user
    user_tenant_id = getattr(current_user, "tenant_id", None)
    if not user_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant-scoped user has no assigned tenant.",
        )

    # Verify tenant state
    tenant_repo = TenantRepository(db)
    tenant = await tenant_repo.get(user_tenant_id)
    if not tenant or tenant.status != TenantStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is suspended or disabled.",
        )

    # If client passed ?tenant_id=, it MUST match user's tenant_id, otherwise 403 Forbidden!
    if tenant_id is not None:
        if tenant_id != user_tenant_id and tenant_id != tenant.slug:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-tenant access forbidden. You cannot specify another tenant's scope.",
            )

    return TenantContext(current_user, user_tenant_id, is_super_admin=False)


DepTenantContext = Annotated[TenantContext, Depends(dep_tenant_context)]
