"""Unit tests for provenance collection and attachment."""

from app.contracts.canonical_event import CanonicalEvent
from app.models.common import CacheStatus, EnrichmentStatus
from app.provenance.tracker import ProvenanceTracker
from app.providers.base import ProviderOutput


def test_provenance_recording() -> None:
    """Verify operation details are captured into an EnrichmentProvenance record."""
    tracker = ProvenanceTracker(configuration_version="1.0.0")
    output = ProviderOutput(
        status=EnrichmentStatus.SUCCESS,
        data={"res": "ok"},
        confidence=0.88,
        source_reference="cmdb://local",
    )

    rec = tracker.record_operation(
        provider_id="test-provider",
        provider_version="2.1.0",
        enrichment_type="asset",
        output=output,
        cache_status=CacheStatus.MISS,
    )

    assert rec.provider_id == "test-provider"
    assert rec.provider_version == "2.1.0"
    assert rec.enrichment_type == "asset"
    assert rec.confidence == 0.88
    assert rec.result_status == EnrichmentStatus.SUCCESS
    assert rec.cache_status == CacheStatus.MISS


def test_provenance_attachment(sample_canonical_event: CanonicalEvent) -> None:
    """Verify attach_to_event places provenance records in event extensions."""
    tracker = ProvenanceTracker(configuration_version="1.0.0")
    output = ProviderOutput(status=EnrichmentStatus.SUCCESS, data={}, confidence=1.0)
    tracker.record_operation("prov-1", "1.0", "geo", output)
    tracker.record_operation("prov-2", "1.0", "asn", output)

    event = tracker.attach_to_event(sample_canonical_event)
    records = event.extensions["enrichment"]["provenance"]
    assert len(records) == 2
    assert records[0]["provider_id"] == "prov-1"
    assert records[1]["provider_id"] == "prov-2"
