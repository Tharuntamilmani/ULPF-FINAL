"""
Event identity and integrity contracts for the ULPF Integration Layer.

Maintains strict separation between:
1. raw_event_id: M1 immutable evidence identity (generated once on ingest)
2. event.id: Canonical event identity (generated during normalization)
3. correlation_id: Pipeline execution and tracing identity (spanning all hops)

Preserves two independent integrity claims:
1. M1 raw_hash: Authoritative SHA-256 over raw byte stream
2. M4 enriched_digest: RFC 8785 canonical JSON digest over enriched event
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class EventIntegrityRecord(BaseModel):
    """
    Immutable integrity record preserving both raw evidence hash and enriched digest.
    Never overwrite one with the other.
    """
    raw_hash: str = Field(..., description="Authoritative SHA-256 calculated by M1 over original raw bytes")
    raw_hash_algorithm: str = Field(default="sha256", description="Digest algorithm for raw hash")
    raw_storage_ref: Optional[str] = Field(default=None, description="Object key in raw storage vault (MinIO/S3)")
    
    # Populated after M4 enrichment
    enriched_digest: Optional[str] = Field(default=None, description="RFC 8785 + SHA-256 calculated by M4")
    enriched_digest_algorithm: Optional[str] = Field(default="sha256", description="Digest algorithm for enriched event")
    signature: Optional[str] = Field(default=None, description="Optional cryptographic signature")
    public_key: Optional[str] = Field(default=None, description="Public key identifier for signature verification")

    def to_m3_integrity(self) -> Dict[str, Any]:
        """Convert to M3's nested integrity structure."""
        return {
            "hash": {
                "algorithm": self.raw_hash_algorithm,
                "value": self.raw_hash,
            }
        }

    def to_m4_raw_integrity(self) -> Dict[str, Any]:
        """Convert to M4's raw integrity block."""
        return {
            "algorithm": self.raw_hash_algorithm,
            "hash": self.raw_hash,
            "raw_storage_ref": self.raw_storage_ref,
        }


class EventIdentity(BaseModel):
    """
    Enforces distinct identities across the pipeline.
    """
    raw_event_id: str = Field(..., description="M1 immutable evidence UUID")
    canonical_event_id: Optional[str] = Field(default=None, description="M3 canonical event UUID")
    correlation_id: str = Field(..., description="Pipeline trace correlation UUID")
    tenant_id: str = Field(..., description="Tenant identifier")
    source_id: str = Field(..., description="Source identifier")

    def validate_distinctness(self) -> bool:
        """
        Verify that raw_event_id and canonical_event_id are not improperly conflated
        if both are present.
        """
        if self.canonical_event_id and self.canonical_event_id == self.raw_event_id:
            # They should normally be distinct concepts
            return False
        return True
