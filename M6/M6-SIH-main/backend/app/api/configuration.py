"""
Configuration Distribution API.
GET  /api/v1/configuration                  – current Redis config snapshot
GET  /api/v1/configuration/status/{config_id} – real-time distribution status of M1–M5 targets
POST /api/v1/configuration/ack              – process module acknowledgement
GET  /api/v1/configuration/version          – current monotonic config version
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.core.dependencies import DepDB
from backend.app.core.rbac import (
    ADMIN,
    SEC_ANALYST,
    SUPER_ADMIN,
    VIEWER,
    require_roles,
)
from backend.app.schemas.config_distribution import DistributionStatusResponse, ModuleAckRequest
from backend.app.services.config_service import ConfigDistributionService

router = APIRouter(prefix="/configuration")

VALID_KEYS = {"sources", "parsers", "schemas", "mappings", "policies"}


@router.get("", response_model=dict[str, Any])
async def get_configuration(
    db: DepDB,
    current_user: Annotated[
        object, Depends(require_roles(SUPER_ADMIN, ADMIN, SEC_ANALYST, VIEWER))
    ],
) -> dict[str, Any]:
    """Return current configuration snapshot from Redis."""
    svc = ConfigDistributionService(db)
    return await svc.get_current_config()


@router.get("/status/{config_id}", response_model=DistributionStatusResponse)
async def get_distribution_status(
    config_id: str,
    db: DepDB,
    current_user: Annotated[
        object, Depends(require_roles(SUPER_ADMIN, ADMIN, SEC_ANALYST, VIEWER))
    ],
) -> DistributionStatusResponse:
    """Return REAL persisted distribution state across M1-M5 target modules."""
    svc = ConfigDistributionService(db)
    res = await svc.get_distribution_status(config_id)
    return DistributionStatusResponse.model_validate(res)


@router.post("/ack")
async def receive_module_ack(
    data: ModuleAckRequest,
    db: DepDB,
) -> dict[str, Any]:
    """
    Process module configuration acknowledgement (APPLIED, REJECTED, FAILED).
    Enforces idempotency, version consistency, and target module verification.
    """
    svc = ConfigDistributionService(db)
    res = await svc.process_ack(
        distribution_id=data.distribution_id,
        config_id=data.config_id,
        version=data.version,
        module=data.module,
        status=data.status,
        correlation_id=data.correlation_id,
        error=data.error,
    )
    if not res.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res.get("reason", "ACK processing failed"),
        )
    return res


@router.get("/version", response_model=dict[str, Any])
async def get_config_version(
    db: DepDB,
    current_user: Annotated[
        object, Depends(require_roles(SUPER_ADMIN, ADMIN, SEC_ANALYST, VIEWER))
    ],
) -> dict[str, Any]:
    """Return the current monotonic config version from Redis."""
    svc = ConfigDistributionService(db)
    version = await svc.get_config_version()
    return {"version": version}
