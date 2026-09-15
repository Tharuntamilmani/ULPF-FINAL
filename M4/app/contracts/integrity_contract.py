"""Integrity contract model for ULPF M4."""

import re
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.common import CanonicalizationAlgorithm, IntegrityAlgorithm

SHA256_HEX_REGEX = re.compile(r"^[0-9a-f]{64}$")


class IntegrityMetadata(BaseModel):
    """Cryptographic integrity metadata.

    IMPORTANT: Hashing guarantees tamper-evident integrity and canonical consistency;
    it does NOT claim authenticity or non-repudiation without digital signatures/PKI.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    algorithm: IntegrityAlgorithm = Field(
        default=IntegrityAlgorithm.SHA256, description="Cryptographic hash algorithm used"
    )
    digest: str = Field(..., description="Hexadecimal representation of the hash digest")
    canonicalization: CanonicalizationAlgorithm = Field(
        default=CanonicalizationAlgorithm.RFC8785,
        description="Canonical serialization algorithm applied",
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 UTC timestamp when digest was generated",
    )
    phase: str = Field(
        default="enriched",
        description="Pipeline phase of the event hashed (raw, canonical, enriched)",
    )

    @field_validator("digest")
    @classmethod
    def validate_digest_hex(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if not SHA256_HEX_REGEX.match(v_clean):
            raise ValueError(f"Invalid SHA-256 hex digest: {v}")
        return v_clean
