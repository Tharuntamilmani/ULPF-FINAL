"""
M6 Prometheus metrics registry.

All metrics defined here. Collected by /metrics endpoint.
Counter/gauge names follow: ulpf_m6_<subsystem>_<name>
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# ── API metrics ───────────────────────────────────────────────────────────────
api_requests_total = Counter(
    "ulpf_m6_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status_code"],
)

api_request_latency_seconds = Histogram(
    "ulpf_m6_api_request_latency_seconds",
    "API request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# ── Registry operations ───────────────────────────────────────────────────────
registry_operations_total = Counter(
    "ulpf_m6_registry_operations_total",
    "Registry CRUD operations",
    ["registry", "operation", "result"],
)

# ── Configuration distribution ────────────────────────────────────────────────
configuration_changes_total = Counter(
    "ulpf_m6_configuration_changes_total",
    "Configuration distribution events",
    ["config_key", "status"],
)

config_version = Gauge(
    "ulpf_m6_config_version",
    "Current configuration version",
)

# ── Audit ─────────────────────────────────────────────────────────────────────
audit_events_total = Counter(
    "ulpf_m6_audit_events_total",
    "Audit events recorded",
    ["action", "result"],
)

# ── Replay ────────────────────────────────────────────────────────────────────
replay_operations_total = Counter(
    "ulpf_m6_replay_operations_total",
    "Replay operation requests",
    ["status"],
)

# ── Service health ────────────────────────────────────────────────────────────
service_health_checks_total = Counter(
    "ulpf_m6_service_health_checks_total",
    "Total health checks performed",
    ["service"],
)

service_health_status = Gauge(
    "ulpf_m6_service_health_status",
    "Current health status of external services (1=HEALTHY, 0=UNHEALTHY/UNAVAILABLE)",
    ["service"],
)

# ── Infrastructure health ─────────────────────────────────────────────────────
kafka_health = Gauge(
    "ulpf_m6_kafka_health",
    "Kafka health (1=healthy, 0=unhealthy)",
)

redis_health = Gauge(
    "ulpf_m6_redis_health",
    "Redis health (1=healthy, 0=unhealthy)",
)

postgres_health = Gauge(
    "ulpf_m6_postgres_health",
    "PostgreSQL health (1=healthy, 0=unhealthy)",
)

opensearch_health = Gauge(
    "ulpf_m6_opensearch_health",
    "OpenSearch health (1=healthy, 0=unhealthy)",
)

minio_health = Gauge(
    "ulpf_m6_minio_health",
    "MinIO health (1=healthy, 0=unhealthy)",
)

# ── Registry statistics ───────────────────────────────────────────────────────
sources_total = Gauge("ulpf_m6_sources_total", "Total registered sources")
parsers_total = Gauge("ulpf_m6_parsers_total", "Total registered parsers")
active_parsers = Gauge("ulpf_m6_parsers_active", "Active parsers")
schemas_total = Gauge("ulpf_m6_schemas_total", "Total registered schemas")
mappings_total = Gauge("ulpf_m6_mappings_total", "Total registered mappings")
policies_total = Gauge("ulpf_m6_policies_total", "Total registered policies")
active_policies = Gauge("ulpf_m6_policies_active", "Active (enabled) policies")


def update_health_gauge(service: str, is_healthy: bool) -> None:
    """Update the service health gauge. 1=healthy, 0=not healthy."""
    service_health_status.labels(service=service).set(1 if is_healthy else 0)
    # Update specific infra gauges
    mapping = {
        "kafka": kafka_health,
        "redis": redis_health,
        "postgres": postgres_health,
        "opensearch": opensearch_health,
        "minio": minio_health,
    }
    if service in mapping:
        mapping[service].set(1 if is_healthy else 0)
