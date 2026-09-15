"""
HttpModuleClient — real HTTP adapter for external services.
Used in production when M1–M5 / infra services have running endpoints.

Never fabricates health. Reports UNAVAILABLE on any connection failure.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger
from backend.app.integrations.module_client import (
    HealthStatus,
    ModuleClient,
    ServiceHealthResult,
)

logger = get_logger("http_module_client")


class HttpModuleClient(ModuleClient):
    """
    Generic HTTP client that calls /health, /ready, /metrics on a remote service.
    Instantiate for each M1–M5 service by passing the service name and base URL.
    """

    def __init__(self, service_name: str, base_url: str | None) -> None:
        self._service_name = service_name
        self._base_url = base_url.rstrip("/") if base_url else None
        settings = get_settings()
        self._timeout = settings.external_health_timeout_seconds
        self._retries = settings.external_health_retry_attempts

    @property
    def service_name(self) -> str:
        return self._service_name

    @property
    def base_url(self) -> str | None:
        return self._base_url

    async def get_health(self) -> ServiceHealthResult:
        return await self._check_endpoint("/health")

    async def get_readiness(self) -> ServiceHealthResult:
        return await self._check_endpoint("/ready")

    async def get_metrics(self) -> str:
        if not self._base_url:
            return ""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(f"{self._base_url}/metrics")
                if resp.status_code == 200:
                    return resp.text
        except Exception:
            pass
        return ""

    async def get_status(self) -> dict[str, Any]:
        health = await self.get_health()
        return health.as_dict()

    async def _check_endpoint(self, path: str) -> ServiceHealthResult:
        if not self._base_url:
            return ServiceHealthResult(
                service=self._service_name,
                status=HealthStatus.UNAVAILABLE,
                details={"reason": "No base URL configured"},
            )

        url = f"{self._base_url}{path}"
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
            latency_ms = (time.monotonic() - start) * 1000

            if resp.status_code == 200:
                status = HealthStatus.HEALTHY
            elif resp.status_code < 500:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY

            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text[:200]}

            return ServiceHealthResult(
                service=self._service_name,
                status=status,
                latency_ms=round(latency_ms, 2),
                details=body,
            )

        except (httpx.ConnectError, httpx.ConnectTimeout):
            return ServiceHealthResult(
                service=self._service_name,
                status=HealthStatus.UNAVAILABLE,
                details={"reason": "Connection refused"},
            )
        except httpx.TimeoutException:
            return ServiceHealthResult(
                service=self._service_name,
                status=HealthStatus.UNAVAILABLE,
                details={"reason": f"Timeout after {self._timeout}s"},
            )
        except Exception as exc:
            return ServiceHealthResult(
                service=self._service_name,
                status=HealthStatus.UNAVAILABLE,
                details={"reason": str(exc)},
            )

    async def push_configuration(self, event: dict[str, Any]) -> dict[str, Any]:
        """Push configuration event to target module endpoint: POST /config/apply."""
        from datetime import UTC, datetime

        if not self._base_url:
            return {
                "distribution_id": event.get("distribution_id", ""),
                "config_id": event.get("entity_id", "") or event.get("distribution_id", ""),
                "version": str(event.get("version", "1.0.0")),
                "module": self._service_name,
                "status": "FAILED",
                "timestamp": datetime.now(UTC).isoformat(),
                "correlation_id": event.get("correlation_id", ""),
                "error": "No base URL configured for module",
            }

        url = f"{self._base_url}/config/apply"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, json=event)
                if resp.status_code == 200:
                    return dict[str, Any](resp.json())
                return {
                    "distribution_id": event.get("distribution_id", ""),
                    "config_id": event.get("entity_id", "") or event.get("distribution_id", ""),
                    "version": str(event.get("version", "1.0.0")),
                    "module": self._service_name,
                    "status": "FAILED",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "correlation_id": event.get("correlation_id", ""),
                    "error": f"Module returned status {resp.status_code}: {resp.text[:200]}",
                }
        except Exception as exc:
            return {
                "distribution_id": event.get("distribution_id", ""),
                "config_id": event.get("entity_id", "") or event.get("distribution_id", ""),
                "version": str(event.get("version", "1.0.0")),
                "module": self._service_name,
                "status": "FAILED",
                "timestamp": datetime.now(UTC).isoformat(),
                "correlation_id": event.get("correlation_id", ""),
                "error": str(exc),
            }
