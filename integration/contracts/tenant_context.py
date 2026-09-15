"""
Tenant context model for the ULPF Integration Layer.
Carries verified tenant identity, source identity, principal, and correlation ID
across all integration boundaries (M1 -> M2 -> M3 -> M4 -> M5) without allowing
downstream modules or payloads to arbitrarily drop or forge tenant identity.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class TenantContext(BaseModel):
    """
    Immutable integration-level tenant context.
    
    Authority:
      M6 remains the platform control-plane authority.
      The Ingress Security Gateway authenticates external callers and establishes TenantContext.
      The Integration Layer preserves and propagates TenantContext across all module boundaries.
    """
    tenant_id: str = Field(..., description="Authorized tenant identifier (e.g. 'tenant-cisco', 'tenant-windows')")
    source_id: str = Field(..., description="Data source identifier (e.g. 'cisco-asa-fw01', 'win-dc01')")
    authenticated_principal: Optional[str] = Field(default=None, description="Authenticated entity or API key name")
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Pipeline trace correlation ID")
    ingested_at: Optional[str] = Field(default=None, description="ISO-8601 ingestion timestamp")

    def to_headers(self) -> Dict[str, str]:
        """Convert tenant context to trusted inter-service HTTP headers."""
        headers = {
            "X-Tenant-ID": self.tenant_id,
            "X-Source-ID": self.source_id,
            "X-Correlation-ID": self.correlation_id,
        }
        if self.authenticated_principal:
            headers["X-Authenticated-Principal"] = self.authenticated_principal
        return headers

    @classmethod
    def from_headers(cls, headers: Dict[str, str], default_source: str = "unknown") -> "TenantContext":
        """Extract tenant context from incoming HTTP headers with case-insensitivity."""
        normalized = {k.lower(): v for k, v in headers.items()}
        tenant_id = normalized.get("x-tenant-id")
        if not tenant_id:
            raise ValueError("Missing required X-Tenant-ID header")
        
        source_id = normalized.get("x-source-id", default_source)
        correlation_id = normalized.get("x-correlation-id") or str(uuid.uuid4())
        principal = normalized.get("x-authenticated-principal")
        
        return cls(
            tenant_id=tenant_id,
            source_id=source_id,
            authenticated_principal=principal,
            correlation_id=correlation_id,
        )

    def to_m4_tenant_block(self) -> Dict[str, Any]:
        """Produce the canonical tenant block required by M4."""
        return {
            "tenant_id": self.tenant_id,
        }

    def to_m5_tenant_block(self) -> Dict[str, Any]:
        """
        Produce a tenant block compatible with M5 SmartRouter.
        M5 inspects both 'id' and 'tenant_id'.
        """
        return {
            "id": self.tenant_id,
            "tenant_id": self.tenant_id,
        }
