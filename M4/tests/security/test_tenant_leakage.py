"""Security tests for tenant boundary isolation and anti-leakage guardrails."""

import pytest

from app.cache.memory_lru import MemoryLRUCache
from app.contracts.canonical_event import CanonicalEvent
from app.contracts.enrichment_contract import EnrichmentRequest
from app.contracts.provenance_contract import EnrichmentProvenance
from app.enrichment.engine import EnrichmentEngine
from app.errors.exceptions import TenantScopeError
from app.models.common import CacheStatus, EnrichmentStatus
from app.models.tenant import TenantContext
from app.security.tenant_guard import TenantGuard


def test_tenant_cache_key_isolation() -> None:
    """Verify tenant isolation in cache key generation."""
    key_a = TenantGuard.build_tenant_cache_key("tenant_a", "p1", "asset", "10.0.0.1")
    key_b = TenantGuard.build_tenant_cache_key("tenant_b", "p1", "asset", "10.0.0.1")
    assert key_a != key_b
    assert key_a == "tenant_a:p1:asset:10.0.0.1"
    assert key_b == "tenant_b:p1:asset:10.0.0.1"


def test_cross_tenant_cache_tampering_blocked() -> None:
    """Ensure Tenant B cannot overwrite Tenant A's cached entries."""
    cache = MemoryLRUCache(max_size=100)
    prov = EnrichmentProvenance(
        provider_id="prov1",
        provider_version="1.0.0",
        enrichment_type="asset",
        confidence=1.0,
        result_status=EnrichmentStatus.SUCCESS,
        cache_status=CacheStatus.MISS,
    )

    # Tenant A sets confidential asset record
    cache.set("tenant_a", "prov1", "asset", "10.0.0.5", {"confidential": "A"}, prov, 60)

    # Tenant B sets same lookup key with their own data
    cache.set("tenant_b", "prov1", "asset", "10.0.0.5", {"confidential": "B"}, prov, 60)

    # Verify neither overwrote the other
    entry_a = cache.get("tenant_a", "prov1", "asset", "10.0.0.5")
    entry_b = cache.get("tenant_b", "prov1", "asset", "10.0.0.5")
    assert entry_a is not None
    assert entry_b is not None
    assert entry_a.data["confidential"] == "A"
    assert entry_b.data["confidential"] == "B"


def test_cross_tenant_event_submission_rejected(
    fresh_engine: EnrichmentEngine, sample_canonical_event: CanonicalEvent
) -> None:
    """If request context specifies Tenant B, but event declares Tenant A, reject immediately."""
    impostor_context = TenantContext(tenant_id="tenant_beta")
    # sample_canonical_event belongs to tenant_alpha
    req = EnrichmentRequest(event=sample_canonical_event, tenant_context=impostor_context)

    with pytest.raises(TenantScopeError, match="Tenant mismatch"):
        fresh_engine.process(req)


def test_tenant_id_directory_traversal_rejected() -> None:
    """Ensure path traversal patterns in tenant IDs are rejected at model boundary."""
    with pytest.raises(ValueError, match="Invalid tenant_id format"):
        TenantContext(tenant_id="../../../etc/passwd")

    with pytest.raises(ValueError, match="Invalid tenant_id format"):
        TenantContext(tenant_id="tenant\x00nullbyte")

    with pytest.raises(ValueError, match="Invalid tenant_id format"):
        TenantContext(tenant_id="tenant;DROP TABLE tenants;")
