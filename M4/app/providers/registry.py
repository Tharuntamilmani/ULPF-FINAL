"""Provider Registry for ULPF M4."""

from app.providers.base import EnrichmentProvider, ProviderMetadata


class ProviderRegistry:
    """Registry maintaining available enrichment providers."""

    def __init__(self) -> None:
        self._providers: dict[str, EnrichmentProvider] = {}

    def register(self, provider: EnrichmentProvider) -> None:
        """Register a provider instance."""
        self._providers[provider.provider_id] = provider

    def unregister(self, provider_id: str) -> bool:
        """Unregister a provider by id."""
        return self._providers.pop(provider_id, None) is not None

    def get(self, provider_id: str) -> EnrichmentProvider | None:
        """Retrieve a provider instance."""
        return self._providers.get(provider_id)

    def list_providers(self) -> list[ProviderMetadata]:
        """List metadata for all registered providers."""
        return [p.metadata for p in self._providers.values()]

    def list_provider_instances(self) -> list[EnrichmentProvider]:
        """Return all provider instances."""
        return list(self._providers.values())

    def clear(self) -> None:
        """Clear all registered providers."""
        self._providers.clear()
