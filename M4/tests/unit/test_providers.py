"""Unit tests for individual enrichment providers."""

import pytest

from app.contracts.canonical_event import CanonicalEvent
from app.errors.exceptions import ProviderTimeoutError
from app.models.common import EnrichmentStatus
from app.models.tenant import TenantContext
from app.providers.asset_provider import LocalAssetProvider
from app.providers.base import EnrichmentContext
from app.providers.geoip_provider import LocalGeoIPProvider
from app.providers.mock_provider import MockEnrichmentProvider
from app.providers.threat_intel_provider import LocalThreatIntelProvider


def test_asset_provider_success(
    sample_canonical_event: CanonicalEvent, sample_tenant_context: TenantContext
) -> None:
    """Verify LocalAssetProvider correctly resolves known asset by source IP."""
    provider = LocalAssetProvider()
    context = EnrichmentContext(tenant_context=sample_tenant_context)
    assert provider.can_enrich(sample_canonical_event, context) is True

    output = provider.enrich(sample_canonical_event, context)
    assert output.status == EnrichmentStatus.SUCCESS
    assert output.data["asset_id"] == "ASSET-PROD-DB-01"
    assert output.data["criticality"] == "high"
    assert output.confidence > 0.9


def test_asset_provider_not_found(
    sample_canonical_event: CanonicalEvent, sample_tenant_context: TenantContext
) -> None:
    """Verify LocalAssetProvider returns NOT_FOUND for unmapped assets."""
    provider = LocalAssetProvider()
    sample_canonical_event.source.ip = "192.0.2.1"
    sample_canonical_event.host.hostname = None
    sample_canonical_event.host.name = None

    context = EnrichmentContext(tenant_context=sample_tenant_context)
    output = provider.enrich(sample_canonical_event, context)
    assert output.status == EnrichmentStatus.NOT_FOUND
    assert output.confidence == 0.0


def test_geoip_provider_public_ip(
    sample_canonical_event: CanonicalEvent, sample_tenant_context: TenantContext
) -> None:
    """Verify LocalGeoIPProvider resolves public test ranges."""
    provider = LocalGeoIPProvider()
    sample_canonical_event.source.ip = "8.8.8.8"
    context = EnrichmentContext(tenant_context=sample_tenant_context)

    output = provider.enrich(sample_canonical_event, context)
    assert output.status == EnrichmentStatus.SUCCESS
    assert output.data["country_code"] == "US"
    assert output.data["asn"]["number"] == 15169
    assert output.data["asn"]["organization"] == "Google LLC"


def test_geoip_provider_private_ip(
    sample_canonical_event: CanonicalEvent, sample_tenant_context: TenantContext
) -> None:
    """Verify LocalGeoIPProvider handles private networks without error."""
    provider = LocalGeoIPProvider()
    sample_canonical_event.source.ip = "10.0.0.1"
    context = EnrichmentContext(tenant_context=sample_tenant_context)

    output = provider.enrich(sample_canonical_event, context)
    assert output.status == EnrichmentStatus.SUCCESS
    assert output.data["country_code"] == "PRIVATE"


def test_geoip_provider_not_found(
    sample_canonical_event: CanonicalEvent, sample_tenant_context: TenantContext
) -> None:
    """Verify unmapped public IP returns NOT_FOUND."""
    provider = LocalGeoIPProvider()
    sample_canonical_event.source.ip = "150.100.20.1"
    context = EnrichmentContext(tenant_context=sample_tenant_context)

    output = provider.enrich(sample_canonical_event, context)
    assert output.status == EnrichmentStatus.NOT_FOUND


def test_threat_intel_provider_malicious_domain(
    sample_canonical_event: CanonicalEvent, sample_tenant_context: TenantContext
) -> None:
    """Verify LocalThreatIntelProvider identifies malicious domain."""
    provider = LocalThreatIntelProvider()
    context = EnrichmentContext(tenant_context=sample_tenant_context)
    assert provider.can_enrich(sample_canonical_event, context) is True

    output = provider.enrich(sample_canonical_event, context)
    assert output.status == EnrichmentStatus.SUCCESS
    assert output.data["verdict"] == "malicious"
    assert output.confidence >= 0.95


def test_threat_intel_provider_clean(
    sample_canonical_event: CanonicalEvent, sample_tenant_context: TenantContext
) -> None:
    """Verify clean indicators return NOT_FOUND."""
    provider = LocalThreatIntelProvider()
    sample_canonical_event.destination.domain = "safe-domain.example.com"
    sample_canonical_event.destination.ip = "1.1.1.1"
    sample_canonical_event.source.ip = "10.0.0.1"
    context = EnrichmentContext(tenant_context=sample_tenant_context)

    output = provider.enrich(sample_canonical_event, context)
    assert output.status == EnrichmentStatus.NOT_FOUND


def test_mock_provider_configurable_behaviors(
    sample_canonical_event: CanonicalEvent, sample_tenant_context: TenantContext
) -> None:
    """Test MockEnrichmentProvider with forced failure, timeout, and not found."""
    context = EnrichmentContext(tenant_context=sample_tenant_context)

    # Success
    p_ok = MockEnrichmentProvider(mock_data={"key": "val"})
    assert p_ok.enrich(sample_canonical_event, context).status == EnrichmentStatus.SUCCESS

    # Failure
    p_fail = MockEnrichmentProvider(should_fail=True)
    assert p_fail.enrich(sample_canonical_event, context).status == EnrichmentStatus.FAILED

    # Not Found
    p_nf = MockEnrichmentProvider(should_not_found=True)
    assert p_nf.enrich(sample_canonical_event, context).status == EnrichmentStatus.NOT_FOUND

    # Timeout
    p_timeout = MockEnrichmentProvider(should_timeout=True)
    with pytest.raises(ProviderTimeoutError):
        p_timeout.enrich(sample_canonical_event, context)
