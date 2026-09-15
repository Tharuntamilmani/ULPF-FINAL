"""Unit tests for TenantContext validation and TenantGuard boundary checks."""

import pytest

from app.contracts.canonical_event import CanonicalEvent
from app.errors.exceptions import TenantScopeError
from app.models.tenant import TenantContext
from app.security.tenant_guard import TenantGuard


def test_tenant_context_validation() -> None:
    """Validate valid and invalid tenant ID strings."""
    valid = TenantContext(tenant_id="tenant-acme.101")
    assert valid.tenant_id == "tenant-acme.101"

    with pytest.raises(ValueError, match="cannot be empty"):
        TenantContext(tenant_id="   ")

    with pytest.raises(ValueError, match="Invalid tenant_id format"):
        TenantContext(tenant_id="bad/tenant/with/slashes")


def test_tenant_guard_validation(sample_canonical_event: CanonicalEvent) -> None:
    """Ensure TenantGuard detects and raises on tenant mismatches."""
    # Matching context passes
    ctx_matching = TenantContext(tenant_id=sample_canonical_event.tenant.tenant_id)
    TenantGuard.validate_event_tenant(sample_canonical_event, ctx_matching)

    # Non-matching context raises TenantScopeError
    ctx_mismatch = TenantContext(tenant_id="different_tenant")
    with pytest.raises(TenantScopeError, match="Tenant mismatch"):
        TenantGuard.validate_event_tenant(sample_canonical_event, ctx_mismatch)
