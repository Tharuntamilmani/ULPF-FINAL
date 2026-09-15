"""Diagnostic models for tracking provider and pipeline execution."""

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import EnrichmentStatus


class ProviderDiagnostic(BaseModel):
    """Detailed diagnostic execution telemetry for an individual provider."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_id: str
    provider_version: str
    status: EnrichmentStatus
    duration_ms: float
    error_message: str | None = None
    error_type: str | None = None
    cached: bool = False


class EnrichmentDiagnostic(BaseModel):
    """Aggregated diagnostics for a complete enrichment cycle."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    total_duration_ms: float
    providers_attempted: int = 0
    providers_succeeded: int = 0
    providers_failed: int = 0
    providers_timed_out: int = 0
    providers_not_found: int = 0
    provider_diagnostics: list[ProviderDiagnostic] = Field(default_factory=list)
