"""Provenance tracking and audit lineage subsystem for ULPF M4."""

from datetime import UTC, datetime

from app.contracts.canonical_event import CanonicalEvent
from app.contracts.provenance_contract import EnrichmentProvenance
from app.models.common import CacheStatus, EnrichmentStatus
from app.providers.base import ProviderOutput


class ProvenanceTracker:
    """Collects and attaches immutable provenance records to enriched events."""

    def __init__(self, configuration_version: str = "1.0.0") -> None:
        self.configuration_version = configuration_version
        self._records: list[EnrichmentProvenance] = []

    def record_operation(
        self,
        provider_id: str,
        provider_version: str,
        enrichment_type: str,
        output: ProviderOutput,
        cache_status: CacheStatus = CacheStatus.MISS,
    ) -> EnrichmentProvenance:
        """Create and store a provenance record for a provider execution."""
        record = EnrichmentProvenance(
            provider_id=provider_id,
            provider_version=provider_version,
            enrichment_type=enrichment_type,
            lookup_timestamp=datetime.now(UTC).isoformat(),
            confidence=output.confidence if output.status == EnrichmentStatus.SUCCESS else 0.0,
            result_status=output.status,
            source_reference=output.source_reference,
            configuration_version=self.configuration_version,
            cache_status=cache_status,
        )
        self._records.append(record)
        return record

    def get_records(self) -> list[EnrichmentProvenance]:
        """Return all collected provenance records."""
        return list(self._records)

    def attach_to_event(self, event: CanonicalEvent) -> CanonicalEvent:
        """Attach collected provenance records to event.extensions['enrichment']['provenance']."""
        if "enrichment" not in event.extensions:
            event.extensions["enrichment"] = {}

        enrichment_ext = event.extensions["enrichment"]
        if not isinstance(enrichment_ext, dict):
            enrichment_ext = {}
            event.extensions["enrichment"] = enrichment_ext

        enrichment_ext["provenance"] = [record.model_dump(mode="json") for record in self._records]
        return event
