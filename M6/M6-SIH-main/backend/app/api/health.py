"""
Health endpoints:
  GET /health  — M6 process liveness
  GET /ready   — M6 readiness (requires PostgreSQL + Redis)
"""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import ORJSONResponse

router = APIRouter()


@router.get("/health", summary="Liveness probe")
async def liveness() -> ORJSONResponse:
    """Returns 200 if the M6 process is alive."""
    return ORJSONResponse({"status": "ok", "service": "m6-control-plane"})


@router.get("/ready", summary="Readiness probe")
async def readiness() -> ORJSONResponse:
    """
    Checks PostgreSQL and Redis.
    Returns 200 if both are reachable, 503 otherwise.
    """
    import asyncio

    from backend.app.integrations.health_client import check_postgres, check_redis
    from backend.app.integrations.module_client import HealthStatus
    from backend.app.metrics.registry import postgres_health, redis_health

    pg_result, redis_result = await asyncio.gather(check_postgres(), check_redis())

    pg_ok = pg_result.status == HealthStatus.HEALTHY
    redis_ok = redis_result.status == HealthStatus.HEALTHY

    # Update Prometheus gauges
    postgres_health.set(1 if pg_ok else 0)
    redis_health.set(1 if redis_ok else 0)

    overall_ready = pg_ok and redis_ok
    http_status = status.HTTP_200_OK if overall_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return ORJSONResponse(
        status_code=http_status,
        content={
            "ready": overall_ready,
            "checks": {
                "postgres": pg_result.as_dict(),
                "redis": redis_result.as_dict(),
            },
        },
    )
