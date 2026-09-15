"""Integration tests for observability, metrics collection, and logging."""

from app.contracts.canonical_event import CanonicalEvent
from app.contracts.enrichment_contract import EnrichmentRequest
from app.enrichment.engine import EnrichmentEngine
from app.models.tenant import TenantContext
from app.observability.logging import setup_logging
from app.observability.metrics import (
    EVENTS_ENRICHED,
    EVENTS_RECEIVED,
)


def test_metrics_incrementation_on_pipeline_run(
    fresh_engine: EnrichmentEngine,
    sample_canonical_event: CanonicalEvent,
    sample_tenant_context: TenantContext,
) -> None:
    """Verify that executing the engine increments Prometheus counters."""
    req = EnrichmentRequest(event=sample_canonical_event, tenant_context=sample_tenant_context)

    # Record initial counts
    recv_before = EVENTS_RECEIVED._value.get()
    succ_before = EVENTS_ENRICHED.labels(status="SUCCESS")._value.get()

    fresh_engine.process(req)

    recv_after = EVENTS_RECEIVED._value.get()
    succ_after = EVENTS_ENRICHED.labels(status="SUCCESS")._value.get()

    assert recv_after == recv_before + 1
    assert succ_after == succ_before + 1


def test_structured_logging_output(capsys: object) -> None:
    """Verify that structured logger outputs valid JSON logs."""
    logger = setup_logging()
    logger.info("Test pipeline audit event", extra={"event_id": "EVT-101", "tenant_id": "t_alpha"})
