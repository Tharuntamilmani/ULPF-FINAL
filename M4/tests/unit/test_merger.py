"""Unit tests for additive merge engine and preservation invariants."""

import pytest

from app.contracts.canonical_event import CanonicalEvent
from app.enrichment.merger import AdditiveMerger
from app.models.common import EnrichmentStatus
from app.providers.base import ProviderOutput


def test_additive_merger_populates_namespace(sample_canonical_event: CanonicalEvent) -> None:
    """Verify provider output is merged into event.extensions['enrichment'][target_namespace]."""
    output = ProviderOutput(
        status=EnrichmentStatus.SUCCESS,
        data={"country": "US", "city": "San Jose"},
        confidence=0.9,
    )

    enriched = AdditiveMerger.merge_output(sample_canonical_event, "geo", output)
    assert "enrichment" in enriched.extensions
    assert "geo" in enriched.extensions["enrichment"]
    assert enriched.extensions["enrichment"]["geo"]["country"] == "US"
    assert enriched.extensions["enrichment"]["geo"]["city"] == "San Jose"


def test_additive_merger_first_writer_priority(sample_canonical_event: CanonicalEvent) -> None:
    """Higher-precedence writer wins; existing fields are not overwritten."""
    output_high = ProviderOutput(
        status=EnrichmentStatus.SUCCESS,
        data={"score": 100, "source": "authoritative"},
    )
    output_low = ProviderOutput(
        status=EnrichmentStatus.SUCCESS,
        data={"score": 50, "source": "secondary", "extra": "new_val"},
    )

    # First merge high-priority
    AdditiveMerger.merge_output(sample_canonical_event, "custom", output_high)
    # Then merge low-priority
    AdditiveMerger.merge_output(sample_canonical_event, "custom", output_low)

    custom_ns = sample_canonical_event.extensions["enrichment"]["custom"]
    assert custom_ns["score"] == 100  # Preserved from high-priority
    assert custom_ns["source"] == "authoritative"  # Preserved
    assert custom_ns["extra"] == "new_val"  # Non-conflicting added


def test_verify_invariants_raises_on_event_id_modification(
    sample_canonical_event: CanonicalEvent,
) -> None:
    """Modifying event.id must raise ValueError."""
    candidate = sample_canonical_event.model_copy(deep=True)
    candidate.event.id = "MODIFIED-ID"
    with pytest.raises(ValueError, match="event.id altered"):
        AdditiveMerger.verify_invariants(sample_canonical_event, candidate)


def test_verify_invariants_raises_on_raw_event_id_modification(
    sample_canonical_event: CanonicalEvent,
) -> None:
    """Modifying provenance.raw_event_id must raise ValueError."""
    candidate = sample_canonical_event.model_copy(deep=True)
    candidate.provenance.raw_event_id = "MODIFIED-RAW"
    with pytest.raises(ValueError, match="raw_event_id altered"):
        AdditiveMerger.verify_invariants(sample_canonical_event, candidate)


def test_verify_invariants_raises_on_source_ip_modification(
    sample_canonical_event: CanonicalEvent,
) -> None:
    """Modifying source.ip must raise ValueError."""
    candidate = sample_canonical_event.model_copy(deep=True)
    candidate.source.ip = "1.2.3.4"
    with pytest.raises(ValueError, match="source.ip altered"):
        AdditiveMerger.verify_invariants(sample_canonical_event, candidate)


def test_verify_invariants_raises_on_tenant_id_modification(
    sample_canonical_event: CanonicalEvent,
) -> None:
    """Modifying tenant.tenant_id must raise ValueError."""
    candidate = sample_canonical_event.model_copy(deep=True)
    candidate.tenant.tenant_id = "tenant_impostor"
    with pytest.raises(ValueError, match="tenant_id altered"):
        AdditiveMerger.verify_invariants(sample_canonical_event, candidate)
