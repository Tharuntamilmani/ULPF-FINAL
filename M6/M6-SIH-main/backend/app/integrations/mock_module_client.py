"""
MockModuleClient — test/development adapter.

Used when USE_MOCK_ADAPTERS=true (CI, offline dev, standalone demo).
Always reports the service as UNAVAILABLE with is_mock=True.
Does NOT pretend the service is HEALTHY.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.app.integrations.module_client import (
    HealthStatus,
    ModuleClient,
    ServiceHealthResult,
)


class MockModuleClient(ModuleClient):
    """Mock adapter — clearly marks itself as a mock. Used in test/CI only."""

    def __init__(self, service_name: str) -> None:
        self._service_name = service_name
        self.should_fail: bool = False
        self.failure_reason: str = "Simulated mock network failure"
        self.rejection_status: str | None = None  # e.g. "REJECTED"

    @property
    def service_name(self) -> str:
        return self._service_name

    @property
    def base_url(self) -> str | None:
        return None

    async def get_health(self) -> ServiceHealthResult:
        return ServiceHealthResult(
            service=self._service_name,
            status=HealthStatus.UNAVAILABLE,
            details={"reason": "Mock adapter — service not connected", "mock": True},
            is_mock=True,
        )

    async def get_readiness(self) -> ServiceHealthResult:
        return await self.get_health()

    async def get_metrics(self) -> str:
        return f"# MOCK adapter for {self._service_name} — no metrics available\n"

    async def get_status(self) -> dict[str, Any]:
        result = (await self.get_health()).as_dict()
        result["is_mock"] = True
        return result

    async def push_configuration(self, event: dict[str, Any]) -> dict[str, Any]:
        """Simulate module configuration processing."""
        if self.should_fail:
            raise RuntimeError(self.failure_reason)

        status = self.rejection_status or "APPLIED"
        error = "Configuration rejected by module" if status == "REJECTED" else None

        # Ensure module matches ["M1", "M2", "M3", "M4", "M5"]
        mod_name = event.get("target_module")
        if not mod_name:
            s = self._service_name.upper()
            for m in ["M1", "M2", "M3", "M4", "M5"]:
                if m in s:
                    mod_name = m
                    break
            if not mod_name:
                mod_name = "M1"

        return {
            "distribution_id": event.get("distribution_id", ""),
            "config_id": event.get("entity_id", "") or event.get("distribution_id", ""),
            "version": str(event.get("version", "1.0.0")),
            "module": mod_name,
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
            "correlation_id": event.get("correlation_id", ""),
            "error": error,
        }
