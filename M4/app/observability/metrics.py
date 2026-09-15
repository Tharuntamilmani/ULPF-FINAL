"""Prometheus metrics definitions for ULPF M4."""

from prometheus_client import CollectorRegistry, Counter, Histogram

# Dedicated registry for clean testing and avoidance of global collisions
METRICS_REGISTRY = CollectorRegistry(auto_describe=True)

EVENTS_RECEIVED = Counter(
    "m4_events_received_total",
    "Total number of canonical events received for enrichment",
    registry=METRICS_REGISTRY,
)

EVENTS_ENRICHED = Counter(
    "m4_events_enriched_total",
    "Total number of events enriched partitioned by final status",
    ["status"],
    registry=METRICS_REGISTRY,
)

PROVIDER_CALLS = Counter(
    "m4_provider_calls_total",
    "Total provider lookups partitioned by provider_id and outcome status",
    ["provider", "status"],
    registry=METRICS_REGISTRY,
)

PROVIDER_LATENCY = Histogram(
    "m4_provider_latency_seconds",
    "Execution latency of enrichment providers in seconds",
    ["provider"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=METRICS_REGISTRY,
)

CACHE_OPERATIONS = Counter(
    "m4_cache_operations_total",
    "Enrichment cache lookups partitioned by provider and result (hit/miss)",
    ["provider", "result"],
    registry=METRICS_REGISTRY,
)

INTEGRITY_VERIFICATIONS = Counter(
    "m4_integrity_verifications_total",
    "Integrity verification outcomes (valid/invalid)",
    ["result"],
    registry=METRICS_REGISTRY,
)
