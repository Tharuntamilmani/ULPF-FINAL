"""Provenance contract model for ULPF M4."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.common import CacheStatus, EnrichmentStatus


class EnrichmentProvenance(BaseModel):
    """Lineage and audit metadata for a specific enrichment operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_id: str = Field(..., description="Unique identifier of the provider")
    provider_version: str = Field(..., description="Semantic version of the provider")
    enrichment_type: str = Field(
        ..., description="Category of enrichment (e.g. geo, asn, asset, threat_intel)"
    )
    lookup_timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 UTC timestamp of the lookup execution",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score of enrichment between 0.0 and 1.0"
    )
    result_status: EnrichmentStatus = Field(
        ..., description="Status of the provider's enrichment attempt"
    )
    source_reference: str | None = Field(
        default=None, description="External database or feed version reference"
    )
    configuration_version: str = Field(
        default="1.0.0", description="Configuration version under which enrichment executed"
    )
    cache_status: CacheStatus = Field(
        default=CacheStatus.MISS, description="Cache status for this lookup"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {v}")
        return round(v, 4)
