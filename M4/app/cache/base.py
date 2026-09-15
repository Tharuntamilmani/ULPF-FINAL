"""Cache abstraction and interfaces for ULPF M4."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.provenance_contract import EnrichmentProvenance


class CacheEntry(BaseModel):
    """Metadata and payload stored within an enrichment cache entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_id: str
    provider_version: str
    tenant_id: str
    lookup_type: str
    lookup_key: str
    cached_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    ttl_seconds: int
    data: dict[str, Any]
    provenance: EnrichmentProvenance
    is_global: bool = False

    def is_expired(self, current_time: datetime | None = None) -> bool:
        """Evaluate whether this entry has exceeded its TTL."""
        now = current_time or datetime.now(UTC)
        created = datetime.fromisoformat(self.cached_at)
        return (now - created).total_seconds() > self.ttl_seconds


class EnrichmentCache(ABC):
    """Abstract base class for enrichment caching engines."""

    @abstractmethod
    def get(
        self,
        tenant_id: str,
        provider_id: str,
        lookup_type: str,
        lookup_key: str,
        is_global: bool = False,
    ) -> CacheEntry | None:
        """Retrieve an unexpired cache entry."""
        pass

    @abstractmethod
    def set(
        self,
        tenant_id: str,
        provider_id: str,
        lookup_type: str,
        lookup_key: str,
        data: dict[str, Any],
        provenance: EnrichmentProvenance,
        ttl_seconds: int,
        is_global: bool = False,
    ) -> None:
        """Persist a cache entry with TTL."""
        pass

    @abstractmethod
    def invalidate(
        self,
        tenant_id: str,
        provider_id: str,
        lookup_type: str,
        lookup_key: str,
        is_global: bool = False,
    ) -> bool:
        """Remove a specific entry from the cache."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Flush all cache entries."""
        pass

    @abstractmethod
    def size(self) -> int:
        """Return total active entries."""
        pass
