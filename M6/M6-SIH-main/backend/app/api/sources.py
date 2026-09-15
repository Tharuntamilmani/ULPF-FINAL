"""
Source Registry API — complete CRUD + enable/disable with strict tenant isolation.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response

from backend.app.core.dependencies import DepDB
from backend.app.core.rbac import (
    ADMIN,
    PARSER_DEV,
    SEC_ANALYST,
    SUPER_ADMIN,
    TENANT_ADMIN,
    VIEWER,
    get_primary_role,
    require_roles,
)
from backend.app.core.tenant_context import DepTenantContext
from backend.app.models.source import SourceStatus
from backend.app.registry.source_registry import SourceRegistry
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.source import SourceCreate, SourceResponse, SourceUpdate

router = APIRouter(prefix="/sources")

# ── Helpers ────────────────────────────────────────────────────────────────────


def _svc(db: DepDB) -> SourceRegistry:
    return SourceRegistry(db)


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.get("", response_model=PaginatedResponse[SourceResponse])
async def list_sources(
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER)),
    ],
    q: str | None = Query(None, description="Search query"),
    vendor: str | None = Query(None),
    status: SourceStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[SourceResponse]:
    """
    List sources.
    Tenant users see ONLY sources belonging to their authenticated tenant.
    SUPER_ADMIN can see cross-tenant sources or filter by ?tenant_id=.
    """
    svc = _svc(db)
    items, total = await svc.list(
        q=q,
        vendor=vendor,
        status=status,
        tenant_id=ctx.tenant_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[SourceResponse.model_validate(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total // page_size)),
    )


@router.post("", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    data: SourceCreate,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
) -> SourceResponse:
    """Create source for the authenticated tenant."""
    svc = _svc(db)
    effective_tenant = ctx.require_tenant_id()
    source = await svc.create(
        data,
        actor=getattr(current_user, "username", "unknown"),
        actor_role=get_primary_role(current_user),
        tenant_id=effective_tenant,
    )
    return SourceResponse.model_validate(source)


@router.get("/{id}", response_model=SourceResponse)
async def get_source(
    id: str,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER)),
    ],
) -> SourceResponse:
    """Get source by ID, scoped to authenticated tenant."""
    svc = _svc(db)
    source = await svc.get(id, tenant_id=ctx.tenant_id)
    return SourceResponse.model_validate(source)


@router.put("/{id}", response_model=SourceResponse)
async def update_source(
    id: str,
    data: SourceUpdate,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
) -> SourceResponse:
    """Update source scoped to authenticated tenant."""
    svc = _svc(db)
    source = await svc.update(
        id,
        data,
        actor=getattr(current_user, "username", "unknown"),
        actor_role=get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
    )
    return SourceResponse.model_validate(source)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    id: str,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
) -> Response:
    """Delete source scoped to authenticated tenant."""
    svc = _svc(db)
    await svc.delete(
        id,
        actor=getattr(current_user, "username", "unknown"),
        actor_role=get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{id}/enable", response_model=SourceResponse)
async def enable_source(
    id: str,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
) -> SourceResponse:
    """Enable source scoped to authenticated tenant."""
    svc = _svc(db)
    source = await svc.enable(
        id,
        actor=getattr(current_user, "username", "unknown"),
        actor_role=get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
    )
    return SourceResponse.model_validate(source)


@router.post("/{id}/disable", response_model=SourceResponse)
async def disable_source(
    id: str,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
) -> SourceResponse:
    """Disable source scoped to authenticated tenant."""
    svc = _svc(db)
    source = await svc.disable(
        id,
        actor=getattr(current_user, "username", "unknown"),
        actor_role=get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
    )
    return SourceResponse.model_validate(source)
