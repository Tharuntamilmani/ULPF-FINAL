"""
Services health API.
GET /api/v1/services              — all services health
GET /api/v1/services/{service}    — single service health
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path

from backend.app.core.rbac import ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER, require_roles
from backend.app.integrations.health_client import get_all_service_health
from backend.app.integrations.module_client import HealthStatus
from backend.app.metrics.registry import service_health_checks_total, update_health_gauge

router = APIRouter(prefix="/services")


@router.get("")
async def list_services_health(
    current_user: Annotated[object, Depends(require_roles(ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER))],
) -> dict[str, Any]:
    """Aggregate health for all M6-monitored services."""
    result = await get_all_service_health()
    # Update Prometheus gauges
    for svc, data in result.get("services", {}).items():
        service_health_checks_total.labels(service=svc).inc()
        is_healthy = data.get("status") == HealthStatus.HEALTHY.value
        update_health_gauge(svc, is_healthy)
    return result


@router.get("/{service}")
async def get_service_health(
    service: Annotated[str, Path(description="Service key, e.g. m1-ingestion, kafka, redis")],
    current_user: Annotated[object, Depends(require_roles(ADMIN, PARSER_DEV, SEC_ANALYST, VIEWER))],
) -> dict[str, Any]:
    """Get health for a single service."""
    all_health = await get_all_service_health()
    services = all_health.get("services", {})
    if service not in services:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail=f"Service '{service}' not found. Available: {list(services.keys())}",
        )
    result: dict[str, Any] = services[service]
    service_health_checks_total.labels(service=service).inc()
    update_health_gauge(service, result.get("status") == HealthStatus.HEALTHY.value)
    return result
