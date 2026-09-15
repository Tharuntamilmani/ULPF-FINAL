"""Mapping Registry API with tenant extensions."""

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
from backend.app.registry.mapping_registry import MappingRegistry
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.mapping import MappingCreate, MappingResponse, MappingUpdate

router = APIRouter(prefix="/mappings")


def _svc(db: DepDB) -> MappingRegistry:
    return MappingRegistry(db)


@router.get("", response_model=PaginatedResponse[MappingResponse])
async def list_mappings(
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER)),
    ],
    q: str | None = Query(None),
    source_format: str | None = Query(None),
    target_schema: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[MappingResponse]:
    items, total = await _svc(db).list(
        q=q,
        source_format=source_format,
        target_schema=target_schema,
        tenant_id=ctx.tenant_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[MappingResponse.model_validate(m) for m in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total // page_size)),
    )


@router.post("", response_model=MappingResponse, status_code=status.HTTP_201_CREATED)
async def create_mapping(
    data: MappingCreate,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV)),
    ],
) -> MappingResponse:
    mapping = await _svc(db).create(
        data,
        getattr(current_user, "username", "unknown"),
        get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
    )
    return MappingResponse.model_validate(mapping)


@router.get("/resolve/{mapping_id}", response_model=MappingResponse)
async def resolve_mapping(
    mapping_id: str,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER)),
    ],
) -> MappingResponse:
    """Deterministic mapping resolution: tenant extension -> platform baseline -> 404."""
    mapping = await _svc(db).resolve(mapping_id, tenant_id=ctx.tenant_id)
    return MappingResponse.model_validate(mapping)


@router.get("/{id}", response_model=MappingResponse)
async def get_mapping(
    id: str,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER)),
    ],
) -> MappingResponse:
    return MappingResponse.model_validate(await _svc(db).get(id, tenant_id=ctx.tenant_id))


@router.put("/{id}", response_model=MappingResponse)
async def update_mapping(
    id: str,
    data: MappingUpdate,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV)),
    ],
) -> MappingResponse:
    mapping = await _svc(db).update(
        id,
        data,
        getattr(current_user, "username", "unknown"),
        get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
    )
    return MappingResponse.model_validate(mapping)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(
    id: str,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV)),
    ],
) -> Response:
    await _svc(db).delete(
        id,
        getattr(current_user, "username", "unknown"),
        get_primary_role(current_user),
        tenant_id=ctx.tenant_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
