"""
Prometheus Metrics collector for the ULPF Integration Layer.
Collects event rates, transit durations, adapter execution times, and integrity status with bounded cardinality.
"""

from prometheus_client import Counter, Histogram, Gauge

EVENTS_PROCESSED_TOTAL = Counter(
    "ulpf_integration_events_processed_total",
    "Total events processed across integration pipeline boundaries",
    ["stage", "tenant_id", "status"],
)

EVENT_TRANSIT_DURATION_SECONDS = Histogram(
    "ulpf_integration_transit_duration_seconds",
    "End-to-end event transit duration across pipeline boundaries",
    ["stage"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

INTEGRITY_VERIFICATION_STATUS = Counter(
    "ulpf_integration_integrity_verification_total",
    "Integrity check status across boundaries",
    ["phase", "result"],
)

IDEMPOTENCY_DUPLICATES_BLOCKED = Counter(
    "ulpf_integration_duplicates_blocked_total",
    "Total duplicate events suppressed by idempotency guard",
    ["tenant_id"],
)

ACTIVE_PIPELINE_RUNNERS = Gauge(
    "ulpf_integration_active_pipeline_runners",
    "Number of active in-flight pipeline runners",
)
