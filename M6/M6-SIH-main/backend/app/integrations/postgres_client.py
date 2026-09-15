"""PostgreSQL health probe — separate from ORM session."""

from __future__ import annotations

from backend.app.integrations.module_client import HealthStatus, ServiceHealthResult


async def check_postgres_health() -> ServiceHealthResult:
    try:
        import time

        from sqlalchemy import text

        from backend.app.db.session import get_engine

        start = time.monotonic()
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return ServiceHealthResult(
            service="postgres",
            status=HealthStatus.HEALTHY,
            latency_ms=round((time.monotonic() - start) * 1000, 2),
        )
    except Exception as exc:
        return ServiceHealthResult(
            service="postgres",
            status=HealthStatus.UNAVAILABLE,
            details={"reason": str(exc)},
        )
