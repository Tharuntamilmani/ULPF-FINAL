"""Deterministic Additive Merger enforcing Preservation Invariants for ULPF M4."""

from app.contracts.canonical_event import CanonicalEvent
from app.providers.base import ProviderOutput


class AdditiveMerger:
    """Merges enrichment provider results into canonical events additively.

    Guarantees strict preservation of authoritative canonical truth:
    - event.id
    - event.timestamp
    - provenance.raw_event_id
    - tenant.tenant_id
    - source.ip, destination.ip
    - parser and normalization metadata
    """

    @staticmethod
    def verify_invariants(original: CanonicalEvent, candidate: CanonicalEvent) -> None:
        """Verify that core canonical invariants have not been modified."""
        if original.event.id != candidate.event.id:
            raise ValueError(
                f"Preservation invariant violated: event.id altered from "
                f"'{original.event.id}' to '{candidate.event.id}'"
            )
        if original.event.timestamp != candidate.event.timestamp:
            raise ValueError("Preservation invariant violated: event.timestamp altered")
        if original.provenance.raw_event_id != candidate.provenance.raw_event_id:
            raise ValueError("Preservation invariant violated: raw_event_id altered")
        if original.tenant.tenant_id != candidate.tenant.tenant_id:
            raise ValueError("Preservation invariant violated: tenant_id altered")
        if original.source.ip != candidate.source.ip:
            raise ValueError("Preservation invariant violated: source.ip altered")
        if original.destination.ip != candidate.destination.ip:
            raise ValueError("Preservation invariant violated: destination.ip altered")

    @classmethod
    def merge_output(
        cls,
        event: CanonicalEvent,
        target_namespace: str,
        output: ProviderOutput,
    ) -> CanonicalEvent:
        """Merge provider data dictionary into event.extensions['enrichment'][target_namespace].

        Higher priority providers have already written; lower priority providers
        only populate fields that are not yet present (first writer by priority wins).
        """
        if not output.data:
            return event

        if "enrichment" not in event.extensions:
            event.extensions["enrichment"] = {}

        enrichment_root = event.extensions["enrichment"]
        if not isinstance(enrichment_root, dict):
            enrichment_root = {}
            event.extensions["enrichment"] = enrichment_root

        if target_namespace not in enrichment_root:
            enrichment_root[target_namespace] = {}

        namespace_dict = enrichment_root[target_namespace]
        if not isinstance(namespace_dict, dict):
            namespace_dict = {}
            enrichment_root[target_namespace] = namespace_dict

        # Deterministic merge: do not overwrite existing higher-precedence fields
        for k, v in output.data.items():
            if k not in namespace_dict:
                namespace_dict[k] = v

        return event
