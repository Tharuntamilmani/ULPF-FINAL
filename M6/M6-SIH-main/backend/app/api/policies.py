"""Policy Management API with strict tenant isolation."""

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
from backend.app.registry.policy_registry import PolicyRegistry
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.policy import PolicyCreate, PolicyResponse, PolicyUpdate

router = APIRouter(prefix="/policies")


def _svc(db: DepDB) -> PolicyRegistry:
    return PolicyRegistry(db)


@router.get("", response_model=PaginatedResponse[PolicyResponse])
async def list_policies(
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER)),
    ],
    q: str | None = Query(None),
    is_enabled: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[PolicyResponse]:
    items, total = await _svc(db).list(
        q=q,
        is_enabled=is_enabled,
        tenant_id=ctx.tenant_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[PolicyResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total // page_size)),
    )


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    data: PolicyCreate,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
) -> PolicyResponse:
    effective_tenant = ctx.require_tenant_id()
    policy = await _svc(db).create(
        data,
        getattr(current_user, "username", "unknown"),
        get_primary_role(current_user),
        tenant_id=effective_tenant,
    )
    return PolicyResponse.model_validate(policy)


@router.get("/{id}", response_model=PolicyResponse)
async def get_policy(
    id: str,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER)),
    ],
) -> PolicyResponse:
    return PolicyResponse.model_validate(await _svc(db).get(id, tenant_id=ctx.tenant_id))


@router.put("/{id}", response_model=PolicyResponse)
async def update_policy(
    id: str,
    data: PolicyUpdate,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
) -> PolicyResponse:
    policy = await _svc(db).update(
        id,
        data,
        getattr(current_user, "username", "unknown"),
        get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
    )
    return PolicyResponse.model_validate(policy)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    id: str,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
) -> Response:
    await _svc(db).delete(
        id,
        getattr(current_user, "username", "unknown"),
        get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{id}/enable", response_model=PolicyResponse)
async def enable_policy(
    id: str,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
) -> PolicyResponse:
    policy = await _svc(db).enable(
        id,
        getattr(current_user, "username", "unknown"),
        get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
    )
    return PolicyResponse.model_validate(policy)


@router.post("/{id}/disable", response_model=PolicyResponse)
async def disable_policy(
    id: str,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
) -> PolicyResponse:
    policy = await _svc(db).disable(
        id,
        getattr(current_user, "username", "unknown"),
        get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
    )
    return PolicyResponse.model_validate(policy)
