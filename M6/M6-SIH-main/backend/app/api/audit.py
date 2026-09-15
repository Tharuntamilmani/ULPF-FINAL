"""Audit Trail API — read-only access to the append-only audit log with tenant isolation."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.app.core.dependencies import DepDB
from backend.app.core.rbac import (
    ADMIN,
    PARSER_DEV,
    SEC_ANALYST,
    SUPER_ADMIN,
    TENANT_ADMIN,
    VIEWER,
    require_roles,
)
from backend.app.core.tenant_context import DepTenantContext
from backend.app.models.audit_log import AuditAction
from backend.app.repositories.audit_repo import AuditRepository
from backend.app.schemas.audit import AuditLogResponse
from backend.app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/audit")


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[
        object,
        Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER)),
    ],
    actor: str | None = Query(None),
    action: AuditAction | None = Query(None),
    resource_type: str | None = Query(None),
    resource_id: str | None = Query(None),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[AuditLogResponse]:
    repo = AuditRepository(db)
    skip = (page - 1) * page_size
    items, total = await repo.search(
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        tenant_id=ctx.tenant_id,
        since=since,
        until=until,
        skip=skip,
        limit=page_size,
    )
    return PaginatedResponse(
        items=[AuditLogResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total // page_size)),
    )
