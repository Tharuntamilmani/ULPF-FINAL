"""Deterministic Local Asset/CMDB Enrichment Provider for ULPF M4."""

from typing import Any

from app.contracts.canonical_event import CanonicalEvent
from app.models.common import EnrichmentStatus
from app.providers.base import EnrichmentContext, EnrichmentProvider, ProviderOutput

# Default deterministic asset CMDB keyed by (tenant_id, lookup_value)
DEFAULT_ASSET_DATABASE: dict[tuple[str, str], dict[str, Any]] = {
    ("default", "10.100.1.5"): {
        "asset_id": "ASSET-PROD-DB-01",
        "hostname": "prod-sql-cluster-node1",
        "criticality": "high",
        "environment": "production",
        "owner": "database-reliability-team",
        "department": "Infrastructure",
        "compliance_scope": ["pci-dss", "soc2"],
    },
    ("default", "10.100.2.10"): {
        "asset_id": "ASSET-PROD-APP-01",
        "hostname": "checkout-service-01",
        "criticality": "critical",
        "environment": "production",
        "owner": "checkout-eng",
        "department": "Engineering",
        "compliance_scope": ["pci-dss"],
    },
    ("default", "192.168.1.50"): {
        "asset_id": "ASSET-WKS-883",
        "hostname": "corp-laptop-883",
        "criticality": "low",
        "environment": "corporate",
        "owner": "alice@corp.local",
        "department": "Finance",
        "compliance_scope": ["internal-only"],
    },
    ("tenant_alpha", "10.200.0.5"): {
        "asset_id": "ASSET-ALPHA-GW",
        "hostname": "alpha-edge-gateway",
        "criticality": "high",
        "environment": "production",
        "owner": "alpha-security",
        "department": "DevOps",
        "compliance_scope": ["iso27001"],
    },
}


class LocalAssetProvider(EnrichmentProvider):
    """Enriches canonical events with internal organizational asset inventory metadata."""

    def __init__(
        self,
        provider_id: str = "asset-local-cmdb",
        provider_version: str = "1.0.0",
        priority: int = 20,
        timeout_seconds: float = 0.5,
        custom_db: dict[tuple[str, str], dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            provider_id=provider_id,
            provider_version=provider_version,
            target_namespace="asset",
            priority=priority,
            timeout_seconds=timeout_seconds,
            is_tenant_sensitive=True,
        )
        self._db = custom_db if custom_db is not None else DEFAULT_ASSET_DATABASE

    def can_enrich(self, event: CanonicalEvent, context: EnrichmentContext) -> bool:
        # Check if source IP, destination IP, or host name is present
        return bool(
            (event.source and event.source.ip)
            or (event.host and event.host.name)
            or (event.host and event.host.hostname)
        )

    def enrich(self, event: CanonicalEvent, context: EnrichmentContext) -> ProviderOutput:
        tenant_id = context.tenant_context.tenant_id

        # Determine candidate lookup keys in priority order
        candidates: list[str] = []
        if event.source and event.source.ip:
            candidates.append(event.source.ip)
        if event.host and event.host.hostname:
            candidates.append(event.host.hostname)
        if event.host and event.host.name:
            candidates.append(event.host.name)

        # Lookup in CMDB first under tenant_id, then under "default"
        for key in candidates:
            # 1. Tenant-specific match
            if (tenant_id, key) in self._db:
                record = self._db[(tenant_id, key)]
                return ProviderOutput(
                    status=EnrichmentStatus.SUCCESS,
                    data=dict(record),
                    confidence=0.98,
                    source_reference=f"cmdb://tenant/{tenant_id}/{record.get('asset_id')}",
                )
            # 2. Default shared tenant match
            if ("default", key) in self._db:
                record = self._db[("default", key)]
                return ProviderOutput(
                    status=EnrichmentStatus.SUCCESS,
                    data=dict(record),
                    confidence=0.95,
                    source_reference=f"cmdb://shared/{record.get('asset_id')}",
                )

        return ProviderOutput(
            status=EnrichmentStatus.NOT_FOUND,
            confidence=0.0,
            error_message="Asset not found in inventory for given identifiers",
        )
