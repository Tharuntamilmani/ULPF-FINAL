"""Thread-safe bounded in-memory LRU and TTL cache with tenant isolation."""

import threading
from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any

from app.cache.base import CacheEntry, EnrichmentCache
from app.contracts.provenance_contract import EnrichmentProvenance
from app.security.tenant_guard import TenantGuard


class MemoryLRUCache(EnrichmentCache):
    """In-memory thread-safe LRU cache with TTL expiration and tenant key isolation."""

    def __init__(self, max_size: int = 10000) -> None:
        self.max_size = max_size
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()

    def _make_key(
        self,
        tenant_id: str,
        provider_id: str,
        lookup_type: str,
        lookup_key: str,
        is_global: bool,
    ) -> str:
        return TenantGuard.build_tenant_cache_key(
            tenant_id=tenant_id,
            provider_id=provider_id,
            lookup_type=lookup_type,
            lookup_key=lookup_key,
            is_global=is_global,
        )

    def get(
        self,
        tenant_id: str,
        provider_id: str,
        lookup_type: str,
        lookup_key: str,
        is_global: bool = False,
    ) -> CacheEntry | None:
        key = self._make_key(tenant_id, provider_id, lookup_type, lookup_key, is_global)
        with self._lock:
            if key not in self._entries:
                return None

            entry = self._entries[key]
            now = datetime.now(UTC)
            if entry.is_expired(now):
                del self._entries[key]
                return None

            # Move to end for LRU update
            self._entries.move_to_end(key)
            return entry

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
        key = self._make_key(tenant_id, provider_id, lookup_type, lookup_key, is_global)
        entry = CacheEntry(
            provider_id=provider_id,
            provider_version=provenance.provider_version,
            tenant_id=tenant_id,
            lookup_type=lookup_type,
            lookup_key=lookup_key,
            ttl_seconds=ttl_seconds,
            data=data,
            provenance=provenance,
            is_global=is_global,
        )
        with self._lock:
            if key in self._entries:
                self._entries.move_to_end(key)
            elif len(self._entries) >= self.max_size:
                # Evict least recently used (first item)
                self._entries.popitem(last=False)

            self._entries[key] = entry

    def invalidate(
        self,
        tenant_id: str,
        provider_id: str,
        lookup_type: str,
        lookup_key: str,
        is_global: bool = False,
    ) -> bool:
        key = self._make_key(tenant_id, provider_id, lookup_type, lookup_key, is_global)
        with self._lock:
            if key in self._entries:
                del self._entries[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._entries)
