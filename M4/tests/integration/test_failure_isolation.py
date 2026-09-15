"""Integration tests for failure isolation, timeout resilience, and partial enrichment."""

from app.cache.memory_lru import MemoryLRUCache
from app.config.lifecycle import ConfigurationManager
from app.contracts.canonical_event import CanonicalEvent
from app.contracts.enrichment_contract import EnrichmentRequest
from app.enrichment.engine import EnrichmentEngine
from app.integrity.verifier import verify_integrity
from app.models.common import EnrichmentStatus
from app.models.tenant import TenantContext
from app.providers.mock_provider import MockEnrichmentProvider
from app.providers.registry import ProviderRegistry


def test_failure_isolation_single_provider_timeout(
    sample_canonical_event: CanonicalEvent,
    sample_tenant_context: TenantContext,
) -> None:
    """If provider A succeeds and provider B times out, status is PARTIAL and event is preserved."""
    reg = ProviderRegistry()
    p_success = MockEnrichmentProvider(
        provider_id="prov-good",
        target_namespace="good_ns",
        mock_data={"key": "val"},
        priority=10,
    )
    p_timeout = MockEnrichmentProvider(
        provider_id="prov-timeout",
        target_namespace="timeout_ns",
        should_timeout=True,
        priority=20,
    )
    reg.register(p_success)
    reg.register(p_timeout)

    cfg_mgr = ConfigurationManager()
    cfg = cfg_mgr.get_active()
    # Enable our test providers
    updated_cfg = cfg.model_copy(update={"enabled_providers": ["prov-good", "prov-timeout"]})
    cfg_mgr._configs[cfg.version] = updated_cfg

    engine = EnrichmentEngine(registry=reg, config_manager=cfg_mgr, cache=MemoryLRUCache())
    req = EnrichmentRequest(event=sample_canonical_event, tenant_context=sample_tenant_context)

    result = engine.process(req)

    # Must be PARTIAL
    assert result.status == EnrichmentStatus.PARTIAL
    # Successful provider data was merged
    assert "good_ns" in result.event.extensions["enrichment"]
    # Timed out provider data was not fabricated
    assert "timeout_ns" not in result.event.extensions["enrichment"]
    # Diagnostics detail the timeout
    assert result.diagnostics.providers_succeeded == 1
    assert result.diagnostics.providers_timed_out == 1
    # Integrity is still calculated and valid
    assert verify_integrity(result.event) is True


def test_failure_isolation_single_provider_exception(
    sample_canonical_event: CanonicalEvent,
    sample_tenant_context: TenantContext,
) -> None:
    """If a provider raises an unhandled exception, it does not crash pipeline; status is PARTIAL."""
    reg = ProviderRegistry()
    p_good = MockEnrichmentProvider(provider_id="prov-good", target_namespace="good", priority=10)
    p_crash = MockEnrichmentProvider(
        provider_id="prov-crash",
        target_namespace="bad",
        raise_exception=RuntimeError("Hardware failure in provider"),
        priority=20,
    )
    reg.register(p_good)
    reg.register(p_crash)

    cfg_mgr = ConfigurationManager()
    cfg = cfg_mgr.get_active()
    updated_cfg = cfg.model_copy(update={"enabled_providers": ["prov-good", "prov-crash"]})
    cfg_mgr._configs[cfg.version] = updated_cfg

    engine = EnrichmentEngine(registry=reg, config_manager=cfg_mgr, cache=MemoryLRUCache())
    req = EnrichmentRequest(event=sample_canonical_event, tenant_context=sample_tenant_context)

    result = engine.process(req)
    assert result.status == EnrichmentStatus.PARTIAL
    assert result.diagnostics.providers_succeeded == 1
    assert result.diagnostics.providers_failed == 1
    assert "good" in result.event.extensions["enrichment"]
    assert "bad" not in result.event.extensions["enrichment"]


def test_all_providers_failed(
    sample_canonical_event: CanonicalEvent,
    sample_tenant_context: TenantContext,
) -> None:
    """If all providers fail, status is FAILED, and original event is preserved intact."""
    reg = ProviderRegistry()
    reg.register(MockEnrichmentProvider(provider_id="fail1", should_fail=True))
    reg.register(MockEnrichmentProvider(provider_id="fail2", should_fail=True))

    cfg_mgr = ConfigurationManager()
    cfg = cfg_mgr.get_active()
    updated_cfg = cfg.model_copy(update={"enabled_providers": ["fail1", "fail2"]})
    cfg_mgr._configs[cfg.version] = updated_cfg

    engine = EnrichmentEngine(registry=reg, config_manager=cfg_mgr, cache=MemoryLRUCache())
    req = EnrichmentRequest(event=sample_canonical_event, tenant_context=sample_tenant_context)

    result = engine.process(req)
    assert result.status == EnrichmentStatus.FAILED
    assert result.event.event.id == sample_canonical_event.event.id
    assert verify_integrity(result.event) is True


def test_no_applicable_providers_returns_skipped(
    sample_canonical_event: CanonicalEvent,
    sample_tenant_context: TenantContext,
) -> None:
    """If no providers are enabled or applicable, status is SKIPPED."""
    reg = ProviderRegistry()
    cfg_mgr = ConfigurationManager()
    cfg = cfg_mgr.get_active()
    updated_cfg = cfg.model_copy(update={"enabled_providers": []})
    cfg_mgr._configs[cfg.version] = updated_cfg

    engine = EnrichmentEngine(registry=reg, config_manager=cfg_mgr)
    req = EnrichmentRequest(event=sample_canonical_event, tenant_context=sample_tenant_context)

    result = engine.process(req)
    assert result.status == EnrichmentStatus.SKIPPED
    assert result.diagnostics.providers_attempted == 0
