"""Integrity calculation and verification service for ULPF M4."""

import hmac
from datetime import UTC, datetime
from typing import Any

from app.contracts.canonical_event import CanonicalEvent
from app.contracts.integrity_contract import IntegrityMetadata
from app.integrity.hasher import hash_canonical_sha256
from app.models.common import CanonicalizationAlgorithm, IntegrityAlgorithm


def _strip_integrity(data: dict[str, Any]) -> dict[str, Any]:
    """Create shallow copy of event dict with integrity field excluded."""
    clean = dict(data)
    clean.pop("integrity", None)
    return clean


def calculate_integrity(
    event: CanonicalEvent | dict[str, Any], phase: str = "enriched"
) -> IntegrityMetadata:
    """Calculate deterministic SHA-256 integrity metadata for a canonical/enriched event.

    The integrity field itself is excluded from hashing to avoid circularity.
    """
    if isinstance(event, CanonicalEvent):
        event_dict = event.model_dump(mode="json")
    elif isinstance(event, dict):
        event_dict = dict(event)
    else:
        raise TypeError(f"Expected CanonicalEvent or dict, got {type(event).__name__}")

    stripped = _strip_integrity(event_dict)
    digest = hash_canonical_sha256(stripped)

    return IntegrityMetadata(
        algorithm=IntegrityAlgorithm.SHA256,
        digest=digest,
        canonicalization=CanonicalizationAlgorithm.RFC8785,
        generated_at=datetime.now(UTC).isoformat(),
        phase=phase,
    )


def verify_integrity(
    event: CanonicalEvent | dict[str, Any],
    expected_digest: str | None = None,
    phase: str = "enriched",
) -> bool:
    """Verify cryptographic integrity of an event against its recorded or supplied digest.

    Uses constant-time comparison to protect against timing attacks.
    """
    target_digest: str | None = expected_digest

    if target_digest is None:
        if isinstance(event, CanonicalEvent):
            if event.integrity is None or not event.integrity.digest:
                return False
            target_digest = event.integrity.digest
        elif isinstance(event, dict):
            integrity_meta = event.get("integrity")
            if not isinstance(integrity_meta, dict) or "digest" not in integrity_meta:
                return False
            target_digest = str(integrity_meta["digest"])
        else:
            return False

    computed_meta = calculate_integrity(event, phase=phase)
    return hmac.compare_digest(
        computed_meta.digest.lower(),
        target_digest.lower().strip(),
    )
