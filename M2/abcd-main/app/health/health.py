from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import Response

# Prometheus Metrics Definitions
EVENTS_TOTAL = Counter(
    "ulpf_parser_events_total", "Total raw events processed by M2 parser engine"
)
SUCCESS_TOTAL = Counter("ulpf_parser_success_total", "Total events parsed successfully")
FAILURE_TOTAL = Counter("ulpf_parser_failure_total", "Total event parsing failures")
UNKNOWN_TOTAL = Counter(
    "ulpf_parser_unknown_total", "Total events classified as unknown source"
)
LATENCY_SECONDS = Histogram(
    "ulpf_parser_latency_seconds", "Latency distribution of parsing in seconds"
)
CONFIDENCE_GAUGE = Gauge("ulpf_parser_confidence", "Classification confidence score")
REPLAY_TOTAL = Counter("ulpf_parser_replay_total", "Total events replayed")
DISCOVERY_TOTAL = Counter(
    "ulpf_parser_discovery_total", "Total unknown-source discovery operations"
)
REGISTRY_SIZE = Gauge("ulpf_parser_registry_size", "Total active parsers in registry")


def get_metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
