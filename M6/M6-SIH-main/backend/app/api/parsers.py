"""
Parser Registry API — CRUD + full lifecycle transitions with tenant extensions.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

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
from backend.app.models.parser import ParserStatus
from backend.app.registry.parser_registry import ParserRegistry
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.parser import (
    ParserCreate,
    ParserLifecycleRequest,
    ParserResponse,
    ParserUpdate,
    ParserVersionResponse,
)

router = APIRouter(prefix="/parsers")


def _svc(db: DepDB) -> ParserRegistry:
    return ParserRegistry(db)


@router.get("", response_model=PaginatedResponse[ParserResponse])
async def list_parsers(
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER)),
    ],
    q: str | None = Query(None),
    status: ParserStatus | None = Query(None),
    vendor: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[ParserResponse]:
    items, total = await _svc(db).list(
        q=q,
        status=status,
        vendor=vendor,
        tenant_id=ctx.tenant_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[ParserResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total // page_size)),
    )


@router.post("", response_model=ParserResponse, status_code=status.HTTP_201_CREATED)
async def register_parser(
    data: ParserCreate,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV)),
    ],
) -> ParserResponse:
    parser = await _svc(db).register(
        data,
        getattr(current_user, "username", "unknown"),
        get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
    )
    return ParserResponse.model_validate(parser)


@router.get("/resolve/{parser_id}", response_model=ParserResponse)
async def resolve_parser(
    parser_id: str,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER)),
    ],
) -> ParserResponse:
    """Deterministic parser resolution: tenant extension -> platform baseline -> 404."""
    parser = await _svc(db).resolve(parser_id, tenant_id=ctx.tenant_id)
    return ParserResponse.model_validate(parser)


@router.get("/{id}", response_model=ParserResponse)
async def get_parser(
    id: str,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER)),
    ],
) -> ParserResponse:
    return ParserResponse.model_validate(await _svc(db).get(id, tenant_id=ctx.tenant_id))


@router.put("/{id}", response_model=ParserResponse)
async def update_parser(
    id: str,
    data: ParserUpdate,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV)),
    ],
) -> ParserResponse:
    parser = await _svc(db).update(
        id,
        data,
        getattr(current_user, "username", "unknown"),
        get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
    )
    return ParserResponse.model_validate(parser)


@router.post("/{id}/submit", response_model=ParserResponse)
async def submit_parser(
    id: str,
    body: ParserLifecycleRequest,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV)),
    ],
) -> ParserResponse:
    parser = await _svc(db).submit(
        id,
        getattr(current_user, "username", "unknown"),
        get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
        reason=body.reason,
    )
    return ParserResponse.model_validate(parser)


@router.post("/{id}/approve", response_model=ParserResponse)
async def approve_parser(
    id: str,
    body: ParserLifecycleRequest,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
) -> ParserResponse:
    parser = await _svc(db).approve(
        id,
        getattr(current_user, "username", "unknown"),
        get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
        reason=body.reason,
    )
    return ParserResponse.model_validate(parser)


@router.post("/{id}/activate", response_model=ParserResponse)
async def activate_parser(
    id: str,
    body: ParserLifecycleRequest,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
) -> ParserResponse:
    parser = await _svc(db).activate(
        id,
        getattr(current_user, "username", "unknown"),
        get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
        reason=body.reason,
    )
    return ParserResponse.model_validate(parser)


@router.post("/{id}/disable", response_model=ParserResponse)
async def disable_parser(
    id: str,
    body: ParserLifecycleRequest,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV)),
    ],
) -> ParserResponse:
    parser = await _svc(db).disable(
        id,
        getattr(current_user, "username", "unknown"),
        get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
        reason=body.reason,
    )
    return ParserResponse.model_validate(parser)


@router.post("/{id}/rollback", response_model=ParserResponse)
async def rollback_parser(
    id: str,
    body: ParserLifecycleRequest,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
) -> ParserResponse:
    parser = await _svc(db).rollback(
        id,
        getattr(current_user, "username", "unknown"),
        get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
        reason=body.reason,
    )
    return ParserResponse.model_validate(parser)


@router.get("/{id}/history", response_model=list[ParserVersionResponse])
async def get_parser_history(
    id: str,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER)),
    ],
) -> list[ParserVersionResponse]:
    versions = await _svc(db).get_history(id, tenant_id=ctx.tenant_id)
    return [ParserVersionResponse.model_validate(v) for v in versions]
