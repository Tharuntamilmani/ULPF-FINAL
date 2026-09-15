"""
ULPF Integration Observability Subsystem.
"""

from integration.observability.health import HealthAggregator, health_app, SystemHealthReport
from integration.observability.metrics import (
    EVENTS_PROCESSED_TOTAL,
    EVENT_TRANSIT_DURATION_SECONDS,
    INTEGRITY_VERIFICATION_STATUS,
    IDEMPOTENCY_DUPLICATES_BLOCKED,
)

__all__ = [
    "HealthAggregator",
    "health_app",
    "SystemHealthReport",
    "EVENTS_PROCESSED_TOTAL",
    "EVENT_TRANSIT_DURATION_SECONDS",
    "INTEGRITY_VERIFICATION_STATUS",
    "IDEMPOTENCY_DUPLICATES_BLOCKED",
]
