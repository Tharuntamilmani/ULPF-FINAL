"""Unit tests for bounded LRU & TTL in-memory cache and tenant key isolation."""

import time

from app.cache.memory_lru import MemoryLRUCache
from app.contracts.provenance_contract import EnrichmentProvenance
from app.models.common import CacheStatus, EnrichmentStatus


def make_dummy_provenance(provider_id: str = "mock-prov") -> EnrichmentProvenance:
    return EnrichmentProvenance(
        provider_id=provider_id,
        provider_version="1.0.0",
        enrichment_type="test",
        confidence=1.0,
        result_status=EnrichmentStatus.SUCCESS,
        cache_status=CacheStatus.MISS,
    )


def test_cache_set_and_get() -> None:
    """Verify caching a value and retrieving it before expiration."""
    cache = MemoryLRUCache(max_size=10)
    prov = make_dummy_provenance()

    cache.set(
        tenant_id="tenant_a",
        provider_id="prov_1",
        lookup_type="asset",
        lookup_key="10.0.0.1",
        data={"name": "srv1"},
        provenance=prov,
        ttl_seconds=10,
    )

    entry = cache.get("tenant_a", "prov_1", "asset", "10.0.0.1")
    assert entry is not None
    assert entry.data["name"] == "srv1"
    assert entry.tenant_id == "tenant_a"


def test_cache_ttl_expiration() -> None:
    """Verify cache entries expire after TTL elapses."""
    cache = MemoryLRUCache(max_size=10)
    prov = make_dummy_provenance()

    # Set with 0 second TTL
    cache.set(
        tenant_id="tenant_a",
        provider_id="prov_1",
        lookup_type="asset",
        lookup_key="10.0.0.1",
        data={"name": "srv1"},
        provenance=prov,
        ttl_seconds=0,
    )

    time.sleep(0.01)
    assert cache.get("tenant_a", "prov_1", "asset", "10.0.0.1") is None


def test_cache_lru_eviction() -> None:
    """Verify oldest unaccessed item is evicted when capacity is exceeded."""
    cache = MemoryLRUCache(max_size=2)
    prov = make_dummy_provenance()

    cache.set("t1", "p1", "type", "k1", {"v": 1}, prov, ttl_seconds=60)
    cache.set("t1", "p1", "type", "k2", {"v": 2}, prov, ttl_seconds=60)
    # Access k1 to make it more recently used
    _ = cache.get("t1", "p1", "type", "k1")

    # Add 3rd item -> k2 should be evicted
    cache.set("t1", "p1", "type", "k3", {"v": 3}, prov, ttl_seconds=60)

    assert cache.get("t1", "p1", "type", "k1") is not None
    assert cache.get("t1", "p1", "type", "k2") is None
    assert cache.get("t1", "p1", "type", "k3") is not None


def test_cache_tenant_isolation() -> None:
    """Verify Tenant A cannot access Tenant B's cached entry."""
    cache = MemoryLRUCache(max_size=10)
    prov = make_dummy_provenance()

    cache.set("tenant_alpha", "p1", "asset", "10.0.0.5", {"secret": "alpha_data"}, prov, 60)

    # Tenant Beta attempts to access identical lookup key
    entry_beta = cache.get("tenant_beta", "p1", "asset", "10.0.0.5")
    assert entry_beta is None

    # Tenant Alpha can access it
    entry_alpha = cache.get("tenant_alpha", "p1", "asset", "10.0.0.5")
    assert entry_alpha is not None
    assert entry_alpha.data["secret"] == "alpha_data"


def test_cache_invalidation_and_clear() -> None:
    """Verify manual invalidation and full cache clearing."""
    cache = MemoryLRUCache(max_size=10)
    prov = make_dummy_provenance()

    cache.set("t1", "p1", "type", "k1", {"v": 1}, prov, 60)
    assert cache.size() == 1

    assert cache.invalidate("t1", "p1", "type", "k1") is True
    assert cache.size() == 0
    assert cache.get("t1", "p1", "type", "k1") is None

    cache.set("t1", "p1", "type", "k2", {"v": 2}, prov, 60)
    cache.clear()
    assert cache.size() == 0
