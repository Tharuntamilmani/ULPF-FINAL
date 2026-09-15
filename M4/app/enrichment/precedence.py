"""Deterministic provider precedence and conflict resolution for ULPF M4."""

from app.config.enrichment_config import EnrichmentConfiguration
from app.providers.base import EnrichmentProvider


def get_provider_sort_key(
    provider: EnrichmentProvider, config: EnrichmentConfiguration
) -> tuple[int, int, str]:
    """Compute deterministic sort key for provider execution and precedence.

    Order:
    1. Explicit configured priority in config.provider_priorities (lowest number first)
    2. Provider intrinsic default priority (lowest number first)
    3. Deterministic tie-breaker: provider_id lexicographically
    """
    configured_priority = config.provider_priorities.get(provider.provider_id, 100)
    intrinsic_priority = provider.priority
    tie_breaker = provider.provider_id
    return (configured_priority, intrinsic_priority, tie_breaker)


def sort_providers_deterministically(
    providers: list[EnrichmentProvider], config: EnrichmentConfiguration
) -> list[EnrichmentProvider]:
    """Return a new list of providers sorted by strict deterministic precedence."""
    return sorted(providers, key=lambda p: get_provider_sort_key(p, config))
