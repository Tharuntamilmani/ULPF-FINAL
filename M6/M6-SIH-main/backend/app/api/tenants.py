"""
Tenants API — platform-level tenant management.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.audit.audit_service import AuditService
from backend.app.core.dependencies import DepDB, dep_current_user
from backend.app.core.rbac import ADMIN, SUPER_ADMIN, require_roles
from backend.app.models.audit_log import AuditAction
from backend.app.models.tenant import Tenant, TenantStatus
from backend.app.repositories.tenant_repo import TenantRepository
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate

router = APIRouter(prefix="/tenants")


@router.get("", response_model=PaginatedResponse[TenantResponse])
async def list_tenants(
    db: DepDB,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN))],
    status: TenantStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[TenantResponse]:
    """List tenants (SUPER_ADMIN only)."""
    repo = TenantRepository(db)
    skip = (page - 1) * page_size
    items, total = await repo.list_tenants(status=status, skip=skip, limit=page_size)
    return PaginatedResponse(
        items=[TenantResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total // page_size)),
    )


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    data: TenantCreate,
    db: DepDB,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN))],
) -> TenantResponse:
    """Create a new tenant (SUPER_ADMIN only)."""
    repo = TenantRepository(db)
    if await repo.slug_exists(data.slug):
        raise HTTPException(status_code=409, detail=f"Tenant slug '{data.slug}' already exists")

    tenant = Tenant(name=data.name, slug=data.slug, status=data.status)
    tenant = await repo.create(tenant)

    audit = AuditService(db)
    await audit.record(
        actor=getattr(current_user, "username", "unknown"),
        actor_role="SUPER_ADMIN",
        action=AuditAction.TENANT_CREATED,
        resource_type="tenant",
        resource_id=tenant.id,
        tenant_id=tenant.id,
        after_state={"name": tenant.name, "slug": tenant.slug, "status": tenant.status.value},
    )

    return TenantResponse.model_validate(tenant)


@router.get("/{id}", response_model=TenantResponse)
async def get_tenant(
    id: str,
    db: DepDB,
    current_user: Annotated[object, Depends(dep_current_user)],
) -> TenantResponse:
    """Get tenant by ID or slug."""
    is_super = getattr(current_user, "is_super_admin", False) or getattr(
        current_user, "is_superuser", False
    )
    caller_tenant_id = getattr(current_user, "tenant_id", None)

    repo = TenantRepository(db)
    tenant = await repo.get(id)
    if not tenant:
        tenant = await repo.get_by_slug(id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant '{id}' not found")

    # If not super admin, caller must belong to this tenant
    if not is_super and tenant.id != caller_tenant_id:
        raise HTTPException(status_code=403, detail="Cross-tenant access forbidden")

    return TenantResponse.model_validate(tenant)


@router.put("/{id}", response_model=TenantResponse)
async def update_tenant(
    id: str,
    data: TenantUpdate,
    db: DepDB,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN))],
) -> TenantResponse:
    """Update tenant (SUPER_ADMIN only)."""
    repo = TenantRepository(db)
    tenant = await repo.get(id)
    if not tenant:
        tenant = await repo.get_by_slug(id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant '{id}' not found")

    update_dict = data.model_dump(exclude_none=True)
    tenant = await repo.update(tenant, update_dict)

    audit = AuditService(db)
    await audit.record(
        actor=getattr(current_user, "username", "unknown"),
        actor_role="SUPER_ADMIN",
        action=AuditAction.TENANT_UPDATED,
        resource_type="tenant",
        resource_id=tenant.id,
        tenant_id=tenant.id,
        after_state={"name": tenant.name, "slug": tenant.slug, "status": tenant.status.value},
    )

    return TenantResponse.model_validate(tenant)
