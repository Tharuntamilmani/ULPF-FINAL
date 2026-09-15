"""
Security Test Suite: Tenant Spoofing & Ingress Boundary Enforcement.
Verifies IngressSecurityGateway resolving P1-3 (M1 Tenant Header Trust / Spoofing Risk).
"""

import pytest
from fastapi import HTTPException, status
from integration.security.ingress_gateway import IngressSecurityGateway, TENANT_CREDENTIAL_REGISTRY


def test_ingress_authenticates_authorized_client():
    """Valid credentials successfully resolve the bound tenant context."""
    gateway = IngressSecurityGateway()
    # Cisco client presenting authorized prod key
    ctx = gateway.authenticate_client(
        auth_header="Bearer key-tenant-cisco-prod",
        api_key_header=None,
        requested_tenant_header=None,
    )
    assert ctx.tenant_id == "tenant-cisco"
    assert ctx.authenticated_principal == "cisco-log-collector"


def test_ingress_detects_and_blocks_tenant_spoofing():
    """
    If a client authenticated as 'tenant-cisco' attempts to inject 'X-Tenant-ID: tenant-windows',
    the gateway MUST REJECT the request with HTTP 403 Forbidden.
    """
    gateway = IngressSecurityGateway()

    with pytest.raises(HTTPException) as exc_info:
        gateway.authenticate_client(
            auth_header="Bearer key-tenant-cisco-prod",
            api_key_header=None,
            requested_tenant_header="tenant-windows",  # Spoofing attempt!
        )

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "cannot act as tenant" in exc_info.value.detail


def test_ingress_rejects_unauthenticated_request():
    """Requests without valid credentials must be rejected with HTTP 401."""
    gateway = IngressSecurityGateway()

    with pytest.raises(HTTPException) as exc_info:
        gateway.authenticate_client(
            auth_header=None,
            api_key_header="invalid-bogus-key",
            requested_tenant_header="tenant-cisco",
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_ingress_allows_explicit_matching_tenant_header():
    """If client supplies their own authorized tenant ID, request succeeds without friction."""
    gateway = IngressSecurityGateway()
    ctx = gateway.authenticate_client(
        auth_header="Bearer key-tenant-windows-prod",
        api_key_header=None,
        requested_tenant_header="tenant-windows",
    )
    assert ctx.tenant_id == "tenant-windows"
