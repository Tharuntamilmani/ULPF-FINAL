"""
Replay Management API.
POST /api/v1/replay/{event_id}   — request a replay
GET  /api/v1/replay              — list replay operations
GET  /api/v1/replay/{id}         — get single replay operation
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.app.core.dependencies import DepDB
from backend.app.core.rbac import ADMIN, PARSER_DEV, SEC_ANALYST, get_primary_role, require_roles
from backend.app.metrics.registry import replay_operations_total
from backend.app.models.replay import ReplayStatus
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.replay import ReplayRequest, ReplayResponse
from backend.app.services.replay_service import ReplayService

router = APIRouter(prefix="/replay")


def _svc(db: DepDB) -> ReplayService:
    return ReplayService(db)


@router.post("/{event_id}", response_model=ReplayResponse, status_code=201)
async def request_replay(
    event_id: str,
    body: ReplayRequest,
    db: DepDB,
    current_user: Annotated[object, Depends(require_roles(ADMIN, PARSER_DEV, SEC_ANALYST))],
) -> ReplayResponse:
    """Request replay of a specific event by event_id."""
    op = await _svc(db).request_replay(
        event_id=event_id,
        source=body.source,
        reason=body.reason,
        requested_by=current_user.username,  # type: ignore[attr-defined]
        actor_role=get_primary_role(current_user),
    )
    replay_operations_total.labels(status="REQUESTED").inc()
    return ReplayResponse.model_validate(op)


@router.get("", response_model=PaginatedResponse[ReplayResponse])
async def list_replays(
    db: DepDB,
    current_user: Annotated[object, Depends(require_roles(ADMIN, PARSER_DEV, SEC_ANALYST))],
    status: ReplayStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[ReplayResponse]:
    from backend.app.repositories.replay_repo import ReplayRepository

    repo = ReplayRepository(db)
    skip = (page - 1) * page_size
    items, total = await repo.search(
        status=status,
        requested_by=None,
        skip=skip,
        limit=page_size,
    )
    return PaginatedResponse(
        items=[ReplayResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total // page_size)),
    )


@router.get("/{id}", response_model=ReplayResponse)
async def get_replay(
    id: str,
    db: DepDB,
    current_user: Annotated[object, Depends(require_roles(ADMIN, PARSER_DEV, SEC_ANALYST))],
) -> ReplayResponse:
    from backend.app.core.exceptions import ReplayNotFound
    from backend.app.repositories.replay_repo import ReplayRepository

    repo = ReplayRepository(db)
    op = await repo.get(id)
    if not op:
        raise ReplayNotFound(f"Replay operation '{id}' not found")
    return ReplayResponse.model_validate(op)
