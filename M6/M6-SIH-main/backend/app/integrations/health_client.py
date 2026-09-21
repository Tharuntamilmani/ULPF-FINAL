"""
Health client — aggregates health from all M1-M5 + infrastructure services.
Returns structured HealthStatus for each. Never fabricates HEALTHY.
"""

from __future__ import annotations

import asyncio
from typing import Any

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger
from backend.app.integrations.module_client import HealthStatus, ServiceHealthResult

logger = get_logger("health_client")


async def check_postgres() -> ServiceHealthResult:
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


async def check_redis() -> ServiceHealthResult:
    try:
        import time

        from backend.app.integrations.redis_client import get_redis_client

        start = time.monotonic()
        client = await get_redis_client()
        await client.ping()
        return ServiceHealthResult(
            service="redis",
            status=HealthStatus.HEALTHY,
            latency_ms=round((time.monotonic() - start) * 1000, 2),
        )
    except Exception as exc:
        return ServiceHealthResult(
            service="redis",
            status=HealthStatus.UNAVAILABLE,
            details={"reason": str(exc)},
        )


async def check_kafka() -> ServiceHealthResult:
    settings = get_settings()
    if not settings.kafka_enabled:
        return ServiceHealthResult(
            service="kafka",
            status=HealthStatus.UNKNOWN,
            details={"reason": "Kafka disabled in config"},
        )
    try:
        import time

        start = time.monotonic()
        from backend.app.integrations.kafka_client import get_kafka_producer

        producer = await get_kafka_producer()
        if producer and await producer.ping():
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            return ServiceHealthResult(
                service="kafka", status=HealthStatus.HEALTHY, latency_ms=latency_ms
            )
        return ServiceHealthResult(
            service="kafka",
            status=HealthStatus.UNAVAILABLE,
            details={"reason": "Producer ping failed"},
        )
    except Exception as exc:
        return ServiceHealthResult(
            service="kafka",
            status=HealthStatus.UNAVAILABLE,
            details={"reason": str(exc)},
        )


async def check_opensearch() -> ServiceHealthResult:
    settings = get_settings()
    try:
        import time

        start = time.monotonic()
        try:
            from opensearchpy import AsyncOpenSearch

            client = AsyncOpenSearch(
                hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
                http_auth=(settings.opensearch_user, settings.opensearch_password),
                use_ssl=settings.opensearch_use_ssl,
                verify_certs=settings.opensearch_verify_certs,
            )
            await client.ping()
            await client.close()
        except (ImportError, Exception):
            import httpx

            scheme = "https" if settings.opensearch_use_ssl else "http"
            auth = (settings.opensearch_user, settings.opensearch_password) if settings.opensearch_password else None
            async with httpx.AsyncClient(timeout=5, verify=settings.opensearch_verify_certs) as http_client:
                resp = await http_client.get(f"{scheme}://{settings.opensearch_host}:{settings.opensearch_port}", auth=auth)
                if resp.status_code not in (200, 201):
                    raise RuntimeError(f"OpenSearch HTTP {resp.status_code}")

        latency = round((time.monotonic() - start) * 1000, 2)
        return ServiceHealthResult(
            service="opensearch", status=HealthStatus.HEALTHY, latency_ms=latency
        )
    except Exception as exc:
        return ServiceHealthResult(
            service="opensearch",
            status=HealthStatus.UNAVAILABLE,
            details={"reason": str(exc)},
        )


async def check_minio() -> ServiceHealthResult:
    settings = get_settings()
    try:
        import time

        import httpx

        start = time.monotonic()
        scheme = "https" if settings.minio_secure else "http"
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{scheme}://{settings.minio_endpoint}/minio/health/live")
        latency = round((time.monotonic() - start) * 1000, 2)
        status = HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        return ServiceHealthResult(service="minio", status=status, latency_ms=latency)
    except Exception as exc:
        return ServiceHealthResult(
            service="minio",
            status=HealthStatus.UNAVAILABLE,
            details={"reason": str(exc)},
        )


async def check_prometheus() -> ServiceHealthResult:
    settings = get_settings()
    if not settings.prometheus_enabled:
        return ServiceHealthResult(service="prometheus", status=HealthStatus.UNKNOWN)
    try:
        import time

        import httpx

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("http://prometheus:9090/-/healthy")
        latency = round((time.monotonic() - start) * 1000, 2)
        status = HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        return ServiceHealthResult(service="prometheus", status=status, latency_ms=latency)
    except Exception as exc:
        return ServiceHealthResult(
            service="prometheus",
            status=HealthStatus.UNAVAILABLE,
            details={"reason": str(exc)},
        )


async def check_grafana() -> ServiceHealthResult:
    settings = get_settings()
    try:
        import time

        import httpx

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.grafana_url}/api/health")
        latency = round((time.monotonic() - start) * 1000, 2)
        status = HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        return ServiceHealthResult(service="grafana", status=status, latency_ms=latency)
    except Exception as exc:
        return ServiceHealthResult(
            service="grafana",
            status=HealthStatus.UNAVAILABLE,
            details={"reason": str(exc)},
        )


async def get_all_service_health() -> dict[str, Any]:
    """Aggregate health for all M6-owned infrastructure + external M1-M5 modules."""
    from backend.app.integrations.m1_client import get_m1_client
    from backend.app.integrations.m2_client import get_m2_client
    from backend.app.integrations.m3_client import get_m3_client
    from backend.app.integrations.m4_client import get_m4_client
    from backend.app.integrations.m5_client import get_m5_client

    # Run all checks concurrently
    checks = await asyncio.gather(
        check_postgres(),
        check_redis(),
        check_kafka(),
        check_opensearch(),
        check_minio(),
        check_prometheus(),
        check_grafana(),
        get_m1_client().get_health(),
        get_m2_client().get_health(),
        get_m3_client().get_health(),
        get_m4_client().get_health(),
        get_m5_client().get_health(),
        return_exceptions=True,
    )

    results: dict[str, Any] = {}
    for check in checks:
        if isinstance(check, ServiceHealthResult):
            results[check.service] = check.as_dict()
        elif isinstance(check, Exception):
            results["unknown"] = {
                "service": "unknown",
                "status": HealthStatus.UNKNOWN.value,
                "details": {"error": str(check)},
            }

    # Overall M6 platform status
    statuses = [r.get("status") for r in results.values()]
    if all(s == HealthStatus.HEALTHY.value for s in statuses):
        overall = "HEALTHY"
    elif any(s == HealthStatus.UNHEALTHY.value for s in statuses):
        overall = "DEGRADED"
    else:
        overall = "DEGRADED"

    return {
        "overall": overall,
        "services": results,
        "m6_control_plane": "HEALTHY",
    }
