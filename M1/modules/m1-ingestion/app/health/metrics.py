from prometheus_client import Counter, Histogram

INGEST_EVENTS_TOTAL = Counter(
    "ulpf_ingest_events_total",
    "Total events processed by M1 ingestion boundary",
    ["transport", "status", "tenant_id"],
)

INGEST_BYTES_TOTAL = Counter(
    "ulpf_ingest_bytes_total",
    "Total raw payload bytes ingested",
    ["transport"],
)

INGEST_ERRORS_TOTAL = Counter(
    "ulpf_ingest_errors_total",
    "Total ingestion errors encountered",
    ["error_type"],
)

INGEST_REJECTED_TOTAL = Counter(
    "ulpf_ingest_rejected_total",
    "Total events rejected prior to processing (auth/rate limit/validation)",
    ["reason"],
)

RAW_VAULT_WRITE_TOTAL = Counter(
    "ulpf_raw_vault_write_total",
    "Total raw objects written to MinIO vault",
    ["status"],
)

KAFKA_PUBLISH_TOTAL = Counter(
    "ulpf_kafka_publish_total",
    "Total messages published to Kafka bus",
    ["topic"],
)

KAFKA_PUBLISH_ERRORS_TOTAL = Counter(
    "ulpf_kafka_publish_errors_total",
    "Total errors when publishing to Kafka bus",
    ["topic"],
)

INGEST_LATENCY_SECONDS = Histogram(
    "ulpf_ingest_latency_seconds",
    "Latency of ingestion pipeline execution in seconds",
    ["transport"],
)
