"""Unit tests for SHA-256 cryptographic integrity calculation and verification."""

from app.contracts.canonical_event import CanonicalEvent
from app.integrity.hasher import hash_bytes_sha256
from app.integrity.verifier import calculate_integrity, verify_integrity


def test_hash_bytes_sha256_known_vector() -> None:
    """Test SHA-256 with NIST standard empty-string test vector."""
    digest = hash_bytes_sha256(b"")
    assert digest == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_calculate_integrity_generates_valid_metadata(
    sample_canonical_event: CanonicalEvent,
) -> None:
    """Test calculate_integrity returns properly populated metadata."""
    meta = calculate_integrity(sample_canonical_event, phase="enriched")
    assert meta.algorithm.value == "sha256"
    assert len(meta.digest) == 64
    assert meta.canonicalization.value == "rfc8785"
    assert meta.phase == "enriched"


def test_verify_integrity_valid(sample_canonical_event: CanonicalEvent) -> None:
    """Test verification passes when event matches its computed digest."""
    meta = calculate_integrity(sample_canonical_event)
    sample_canonical_event.integrity = meta
    assert verify_integrity(sample_canonical_event) is True
    assert verify_integrity(sample_canonical_event, expected_digest=meta.digest) is True


def test_verify_integrity_detects_field_modification(
    sample_canonical_event: CanonicalEvent,
) -> None:
    """Tampering with an authoritative field must cause verification to fail."""
    meta = calculate_integrity(sample_canonical_event)
    sample_canonical_event.integrity = meta

    # Tamper with source IP
    tampered_event = sample_canonical_event.model_copy(deep=True)
    tampered_event.source.ip = "192.168.99.99"

    assert verify_integrity(tampered_event) is False
    assert verify_integrity(tampered_event, expected_digest=meta.digest) is False


def test_verify_integrity_detects_added_field(sample_canonical_event: CanonicalEvent) -> None:
    """Injecting an extra key into extensions must cause verification to fail."""
    meta = calculate_integrity(sample_canonical_event)
    sample_canonical_event.integrity = meta

    tampered_dict = sample_canonical_event.model_dump(mode="json")
    tampered_dict["extensions"]["injected_backdoor"] = True

    assert verify_integrity(tampered_dict, expected_digest=meta.digest) is False


def test_verify_integrity_detects_removed_field(sample_canonical_event: CanonicalEvent) -> None:
    """Deleting a field must invalidate verification."""
    meta = calculate_integrity(sample_canonical_event)
    sample_canonical_event.integrity = meta

    tampered_dict = sample_canonical_event.model_dump(mode="json")
    del tampered_dict["observer"]

    assert verify_integrity(tampered_dict, expected_digest=meta.digest) is False


def test_verify_integrity_detects_array_reordering(sample_canonical_event: CanonicalEvent) -> None:
    """Reordering items in a semantic array must alter the digest."""
    sample_canonical_event.event.type = ["typeA", "typeB"]
    meta = calculate_integrity(sample_canonical_event)
    sample_canonical_event.integrity = meta

    tampered = sample_canonical_event.model_copy(deep=True)
    tampered.event.type = ["typeB", "typeA"]

    assert verify_integrity(tampered, expected_digest=meta.digest) is False


def test_circular_integrity_exclusion(sample_canonical_event: CanonicalEvent) -> None:
    """Ensure that changing the integrity block does not affect calculate_integrity."""
    meta1 = calculate_integrity(sample_canonical_event)
    sample_canonical_event.integrity = meta1

    # Now calculate again; digest must be identical because integrity field is stripped
    meta2 = calculate_integrity(sample_canonical_event)
    assert meta1.digest == meta2.digest


def test_verify_integrity_missing_digest_returns_false(
    sample_canonical_event: CanonicalEvent,
) -> None:
    """Verifying an event with no integrity metadata returns False."""
    sample_canonical_event.integrity = None
    assert verify_integrity(sample_canonical_event) is False
