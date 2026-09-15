"""Unit tests for deterministic provider precedence and sorting."""

from app.config.enrichment_config import EnrichmentConfiguration
from app.enrichment.precedence import (
    sort_providers_deterministically,
)
from app.providers.mock_provider import MockEnrichmentProvider


def test_precedence_sort_order() -> None:
    """Test priority resolution: configured priority > intrinsic priority > tie-breaker."""
    # Provider A: intrinsic priority 50
    p_a = MockEnrichmentProvider(provider_id="provider-a", priority=50)
    # Provider B: intrinsic priority 20
    p_b = MockEnrichmentProvider(provider_id="provider-b", priority=20)
    # Provider C: intrinsic priority 50, but configured priority 10
    p_c = MockEnrichmentProvider(provider_id="provider-c", priority=50)

    config = EnrichmentConfiguration(
        version="1.0.0",
        provider_priorities={"provider-c": 10},
    )

    # Expected order: provider-c (configured 10), then provider-b (intrinsic 20), then provider-a (intrinsic 50)
    sorted_providers = sort_providers_deterministically([p_a, p_b, p_c], config)
    assert [p.provider_id for p in sorted_providers] == ["provider-c", "provider-b", "provider-a"]


def test_precedence_deterministic_tie_breaker() -> None:
    """Equal priorities must break ties lexicographically by provider_id."""
    p_z = MockEnrichmentProvider(provider_id="provider-z", priority=30)
    p_m = MockEnrichmentProvider(provider_id="provider-m", priority=30)
    p_a = MockEnrichmentProvider(provider_id="provider-a", priority=30)

    config = EnrichmentConfiguration(version="1.0.0")
    sorted_providers = sort_providers_deterministically([p_z, p_m, p_a], config)
    assert [p.provider_id for p in sorted_providers] == ["provider-a", "provider-m", "provider-z"]
