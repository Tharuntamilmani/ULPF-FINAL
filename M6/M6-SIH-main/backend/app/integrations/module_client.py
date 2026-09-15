"""
ModuleClient — abstract base for all external service integration adapters.

Every M1–M5 adapter and infrastructure adapter must implement this interface.
M6 never imports M1–M5 source code. It communicates only through HTTP
using the configured base URL.

When a service is unavailable (connection refused, timeout, etc.):
  - get_health()     returns HealthStatus.UNAVAILABLE
  - get_readiness()  returns ReadinessStatus.UNAVAILABLE
  - get_metrics()    returns empty string
  - get_status()     returns a structured dict with status=UNAVAILABLE

NEVER convert an unavailable service to HEALTHY.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


@dataclass
class ServiceHealthResult:
    service: str
    status: HealthStatus
    latency_ms: float | None = None
    checked_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    details: dict[str, Any] = field(default_factory=dict)
    is_mock: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "checked_at": self.checked_at,
            "details": self.details,
            "is_mock": self.is_mock,
        }


class ModuleClient(abc.ABC):
    """Abstract base for all external service clients."""

    @property
    @abc.abstractmethod
    def service_name(self) -> str: ...

    @property
    @abc.abstractmethod
    def base_url(self) -> str | None: ...

    @abc.abstractmethod
    async def get_health(self) -> ServiceHealthResult: ...

    @abc.abstractmethod
    async def get_readiness(self) -> ServiceHealthResult: ...

    @abc.abstractmethod
    async def get_metrics(self) -> str:
        """Return Prometheus text-format metrics, or empty string."""
        ...

    @abc.abstractmethod
    async def get_status(self) -> dict[str, Any]:
        """Return a structured status summary dict."""
        ...

    @abc.abstractmethod
    async def push_configuration(self, event: dict[str, Any]) -> dict[str, Any]:
        """Push configuration event to target module and return ACK contract."""
        ...
