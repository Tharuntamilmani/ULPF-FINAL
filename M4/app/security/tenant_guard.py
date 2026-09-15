"""Tenant Boundary Enforcement and Guardrails for ULPF M4."""

from app.contracts.canonical_event import CanonicalEvent
from app.errors.exceptions import TenantScopeError
from app.models.tenant import TenantContext


class TenantGuard:
    """Enforces strict tenant isolation across enrichment operations."""

    @staticmethod
    def validate_event_tenant(event: CanonicalEvent, context: TenantContext | None) -> None:
        """Verify that the event's internal tenant matches the authorized context tenant."""
        if context is None:
            return

        event_tenant = event.tenant.tenant_id
        context_tenant = context.tenant_id

        if event_tenant != context_tenant:
            raise TenantScopeError(
                f"Tenant mismatch: Event tenant '{event_tenant}' does not match "
                f"authorized context tenant '{context_tenant}'"
            )

    @staticmethod
    def build_tenant_cache_key(
        tenant_id: str,
        provider_id: str,
        lookup_type: str,
        lookup_key: str,
        is_global: bool = False,
    ) -> str:
        """Generate a tenant-isolated cache key.

        Global cache entries are only allowed when explicitly designated as non-tenant-sensitive.
        """
        effective_tenant = "__global__" if is_global else tenant_id
        return f"{effective_tenant}:{provider_id}:{lookup_type}:{lookup_key}"
