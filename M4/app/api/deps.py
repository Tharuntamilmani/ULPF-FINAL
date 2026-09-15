"""FastAPI Dependency injection providers for ULPF M4."""

from app.cache.memory_lru import MemoryLRUCache
from app.config.lifecycle import ConfigurationManager
from app.enrichment.engine import EnrichmentEngine
from app.providers.asset_provider import LocalAssetProvider
from app.providers.geoip_provider import LocalGeoIPProvider
from app.providers.registry import ProviderRegistry
from app.providers.threat_intel_provider import LocalThreatIntelProvider

# Module-level singletons for application lifecycle
_CACHE = MemoryLRUCache(max_size=10000)
_REGISTRY = ProviderRegistry()
_CONFIG_MGR = ConfigurationManager()

# Pre-register default first-party providers
_REGISTRY.register(LocalAssetProvider())
_REGISTRY.register(LocalGeoIPProvider())
_REGISTRY.register(LocalThreatIntelProvider())

_ENGINE = EnrichmentEngine(
    registry=_REGISTRY,
    config_manager=_CONFIG_MGR,
    cache=_CACHE,
)


def get_cache() -> MemoryLRUCache:
    """Return cache engine instance."""
    return _CACHE


def get_registry() -> ProviderRegistry:
    """Return provider registry instance."""
    return _REGISTRY


def get_config_manager() -> ConfigurationManager:
    """Return configuration manager instance."""
    return _CONFIG_MGR


def get_engine() -> EnrichmentEngine:
    """Return core enrichment engine instance."""
    return _ENGINE
