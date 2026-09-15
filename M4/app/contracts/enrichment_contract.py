"""Enrichment request and result contract models for ULPF M4."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.canonical_event import CanonicalEvent
from app.contracts.integrity_contract import IntegrityMetadata
from app.contracts.provenance_contract import EnrichmentProvenance
from app.models.common import EnrichmentStatus
from app.models.diagnostics import EnrichmentDiagnostic
from app.models.tenant import TenantContext


class EnrichmentRequest(BaseModel):
    """External/API request payload to enrich a canonical UES event."""

    model_config = ConfigDict(extra="forbid")

    event: CanonicalEvent = Field(..., description="Canonical UES event to be enriched")
    tenant_context: TenantContext | None = Field(
        default=None, description="Explicit tenant context overriding event tenant if authorized"
    )
    configuration_version: str | None = Field(
        default=None, description="Specific configuration version to execute against"
    )
    options: dict[str, Any] = Field(
        default_factory=dict, description="Execution options (e.g. bypass_cache=True, dry_run=True)"
    )


class EnrichmentResult(BaseModel):
    """Output payload after M4 enrichment, provenance attachment, and integrity hashing."""

    model_config = ConfigDict(extra="forbid")

    event: CanonicalEvent = Field(..., description="Enriched canonical UES event")
    status: EnrichmentStatus = Field(..., description="Overall enrichment status")
    provenance: list[EnrichmentProvenance] = Field(
        default_factory=list, description="Provenance audit records for all enrichment operations"
    )
    diagnostics: EnrichmentDiagnostic = Field(
        ..., description="Execution telemetry, timings, and provider failure records"
    )
    integrity: IntegrityMetadata = Field(
        ..., description="Calculated cryptographic integrity of the enriched event"
    )
