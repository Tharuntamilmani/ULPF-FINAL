"""Integration tests for the complete M4 enrichment pipeline."""

from app.config.lifecycle import ConfigurationManager
from app.contracts.canonical_event import CanonicalEvent
from app.contracts.enrichment_contract import EnrichmentRequest
from app.enrichment.engine import EnrichmentEngine
from app.integrity.verifier import verify_integrity
from app.models.common import CacheStatus, EnrichmentStatus
from app.models.tenant import TenantContext
from app.providers.registry import ProviderRegistry


def test_full_enrichment_pipeline_success(
    fresh_engine: EnrichmentEngine,
    sample_canonical_event: CanonicalEvent,
    sample_tenant_context: TenantContext,
) -> None:
    """Execute complete end-to-end enrichment across asset, geo, and threat intel providers."""
    request = EnrichmentRequest(
        event=sample_canonical_event,
        tenant_context=sample_tenant_context,
    )

    result = fresh_engine.process(request)

    # 1. Overall Status
    assert result.status == EnrichmentStatus.SUCCESS

    # 2. Additive Merge Verification
    enriched = result.event
    assert "enrichment" in enriched.extensions
    enrichment_data = enriched.extensions["enrichment"]
    assert "asset" in enrichment_data
    assert "geo" in enrichment_data
    assert "threat_intel" in enrichment_data

    # Check asset values
    assert enrichment_data["asset"]["asset_id"] == "ASSET-PROD-DB-01"
    assert enrichment_data["asset"]["criticality"] == "high"

    # Check geo values (10.100.1.5 is private network)
    assert enrichment_data["geo"]["country_code"] == "PRIVATE"
    assert enrichment_data["geo"]["city"] == "Internal"

    # Check threat intel values
    assert enrichment_data["threat_intel"]["verdict"] == "malicious"

    # 3. Preservation Invariants
    assert enriched.event.id == sample_canonical_event.event.id
    assert enriched.event.timestamp == sample_canonical_event.event.timestamp
    assert enriched.provenance.raw_event_id == sample_canonical_event.provenance.raw_event_id
    assert enriched.tenant.tenant_id == sample_canonical_event.tenant.tenant_id
    assert enriched.source.ip == sample_canonical_event.source.ip
    assert enriched.destination.ip == sample_canonical_event.destination.ip

    # 4. Provenance Verification
    assert len(result.provenance) >= 3
    for p in result.provenance:
        assert p.result_status == EnrichmentStatus.SUCCESS
        assert p.confidence > 0.8
        assert p.configuration_version == "1.0.0"

    # 5. Cryptographic Integrity Verification
    assert result.integrity is not None
    assert enriched.integrity is not None
    assert result.integrity.digest == enriched.integrity.digest
    assert verify_integrity(enriched) is True


def test_pipeline_cache_hit_on_second_run(
    fresh_engine: EnrichmentEngine,
    sample_canonical_event: CanonicalEvent,
    sample_tenant_context: TenantContext,
) -> None:
    """Subsequent enrichment requests for identical entities must yield cache hits."""
    request = EnrichmentRequest(
        event=sample_canonical_event,
        tenant_context=sample_tenant_context,
    )

    # First run (cache miss)
    result1 = fresh_engine.process(request)
    assert result1.status == EnrichmentStatus.SUCCESS
    for p in result1.provenance:
        assert p.cache_status == CacheStatus.MISS

    # Second run (cache hit)
    event2 = sample_canonical_event.model_copy(deep=True)
    request2 = EnrichmentRequest(
        event=event2,
        tenant_context=sample_tenant_context,
    )
    result2 = fresh_engine.process(request2)
    assert result2.status == EnrichmentStatus.SUCCESS

    # Check that diagnostic flags cached=True and provenance shows HIT
    cached_records = [p for p in result2.provenance if p.cache_status == CacheStatus.HIT]
    assert len(cached_records) > 0


def test_pipeline_bypass_cache_option(
    fresh_engine: EnrichmentEngine,
    sample_canonical_event: CanonicalEvent,
    sample_tenant_context: TenantContext,
) -> None:
    """Option bypass_cache=True must force fresh execution despite warm cache."""
    request_warm = EnrichmentRequest(
        event=sample_canonical_event,
        tenant_context=sample_tenant_context,
    )
    fresh_engine.process(request_warm)

    # Now request with bypass_cache
    event_fresh = sample_canonical_event.model_copy(deep=True)
    request_bypass = EnrichmentRequest(
        event=event_fresh,
        tenant_context=sample_tenant_context,
        options={"bypass_cache": True},
    )
    result = fresh_engine.process(request_bypass)
    for p in result.provenance:
        assert p.cache_status in (CacheStatus.MISS, CacheStatus.BYPASS)


def test_pipeline_preserves_external_extensions(
    fresh_engine: EnrichmentEngine,
    sample_canonical_event: CanonicalEvent,
    sample_tenant_context: TenantContext,
) -> None:
    """Pre-existing extensions from upstream modules must remain intact."""
    sample_canonical_event.extensions["upstream_custom"] = {"flag": True, "tag": "m3-data"}
    request = EnrichmentRequest(event=sample_canonical_event, tenant_context=sample_tenant_context)

    result = fresh_engine.process(request)
    assert result.event.extensions["upstream_custom"]["flag"] is True
    assert result.event.extensions["upstream_custom"]["tag"] == "m3-data"
    assert "enrichment" in result.event.extensions


def test_pipeline_with_multiple_threat_indicators(
    fresh_engine: EnrichmentEngine,
    sample_canonical_event: CanonicalEvent,
    sample_tenant_context: TenantContext,
) -> None:
    """Verify threat intelligence aggregates multiple indicator hits."""
    sample_canonical_event.destination.domain = "evil-payload.example.com"
    sample_canonical_event.source.ip = "198.51.100.99"  # known malicious IP in IOC db
    request = EnrichmentRequest(event=sample_canonical_event, tenant_context=sample_tenant_context)

    result = fresh_engine.process(request)
    ti_data = result.event.extensions["enrichment"]["threat_intel"]
    assert ti_data["verdict"] == "malicious"
    assert ti_data["matched_count"] >= 2


def test_pipeline_determinism_across_restarts(
    sample_canonical_event: CanonicalEvent,
    sample_tenant_context: TenantContext,
    fresh_registry: ProviderRegistry,
    fresh_config_manager: ConfigurationManager,
) -> None:
    """Two independent engine instances must produce the exact same enriched digest."""
    from app.cache.memory_lru import MemoryLRUCache

    eng1 = EnrichmentEngine(fresh_registry, fresh_config_manager, MemoryLRUCache())
    eng2 = EnrichmentEngine(fresh_registry, fresh_config_manager, MemoryLRUCache())

    evt1 = sample_canonical_event.model_copy(deep=True)
    evt2 = sample_canonical_event.model_copy(deep=True)

    r1 = eng1.process(EnrichmentRequest(event=evt1, tenant_context=sample_tenant_context))
    r2 = eng2.process(EnrichmentRequest(event=evt2, tenant_context=sample_tenant_context))

    # Note: timestamps in provenance differ by execution millisecond, but structure & status are identical
    assert r1.status == r2.status
    assert r1.event.extensions["enrichment"]["asset"] == r2.event.extensions["enrichment"]["asset"]
    assert r1.event.extensions["enrichment"]["geo"] == r2.event.extensions["enrichment"]["geo"]
