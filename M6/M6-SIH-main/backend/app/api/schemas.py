"""Schema Registry API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from backend.app.core.dependencies import DepDB
from backend.app.core.rbac import (
    ADMIN,
    PARSER_DEV,
    SEC_ANALYST,
    VIEWER,
    get_primary_role,
    require_roles,
)
from backend.app.models.user import User
from backend.app.registry.schema_registry import SchemaRegistry
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.schema import (
    SchemaCreate,
    SchemaResponse,
    SchemaVersionCreate,
    SchemaVersionResponse,
)

router = APIRouter(prefix="/schemas")


def _svc(db: DepDB) -> SchemaRegistry:
    return SchemaRegistry(db)


@router.get("", response_model=PaginatedResponse[SchemaResponse])
async def list_schemas(
    db: DepDB,
    current_user: Annotated[object, Depends(require_roles(ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[SchemaResponse]:
    items, total = await _svc(db).list(page=page, page_size=page_size)
    return PaginatedResponse(
        items=[SchemaResponse.model_validate(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total // page_size)),
    )


@router.post("", response_model=SchemaResponse, status_code=status.HTTP_201_CREATED)
async def create_schema(
    data: SchemaCreate,
    db: DepDB,
    current_user: Annotated[User, Depends(require_roles(ADMIN, PARSER_DEV))],
) -> SchemaResponse:
    schema = await _svc(db).create(
        data,
        current_user.username,
        get_primary_role(current_user),
    )
    return SchemaResponse.model_validate(schema)


@router.get("/{name}", response_model=SchemaResponse)
async def get_schema(
    name: str,
    db: DepDB,
    current_user: Annotated[object, Depends(require_roles(ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER))],
) -> SchemaResponse:
    schema = await _svc(db).get(name)
    return SchemaResponse.model_validate(schema)


@router.get("/{name}/{version}", response_model=SchemaVersionResponse)
async def get_schema_version(
    name: str,
    version: str,
    db: DepDB,
    current_user: Annotated[object, Depends(require_roles(ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER))],
) -> SchemaVersionResponse:
    sv = await _svc(db).get_version(name, version)
    return SchemaVersionResponse.model_validate(sv)


@router.post(
    "/{name}/versions", response_model=SchemaVersionResponse, status_code=status.HTTP_201_CREATED
)
async def add_schema_version(
    name: str,
    data: SchemaVersionCreate,
    db: DepDB,
    current_user: Annotated[User, Depends(require_roles(ADMIN, PARSER_DEV))],
) -> SchemaVersionResponse:
    sv = await _svc(db).add_version(
        name,
        data,
        current_user.username,
        get_primary_role(current_user),
    )
    return SchemaVersionResponse.model_validate(sv)
