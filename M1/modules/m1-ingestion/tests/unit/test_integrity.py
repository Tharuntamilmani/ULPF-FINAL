import hashlib
import uuid

import pytest

from app.integrity.hashing import compute_sha256
from app.integrity.ids import generate_uuidv7


def test_uuidv7_generation_valid_and_unique():
    id1 = generate_uuidv7()
    id2 = generate_uuidv7()

    assert id1 != id2

    # Parse as UUID object
    u1 = uuid.UUID(id1)
    u2 = uuid.UUID(id2)

    # Check version 7
    assert u1.version == 7
    assert u2.version == 7

    # Check variant 2 (RFC 4122 / RFC 9562)
    assert u1.variant == uuid.RFC_4122


def test_sha256_hashing_correctness():
    payload = b"hello world"
    expected = hashlib.sha256(payload).hexdigest()

    result = compute_sha256(payload)
    assert result == expected
    assert len(result) == 64


def test_sha256_type_safety():
    with pytest.raises(TypeError):
        compute_sha256("string payload not allowed")  # type: ignore


@pytest.mark.parametrize(
    "payload",
    [
        b"hello",
        b"hello\n",
        b"hello\r\n",
        "Firewall alert: 🚨 unauthorized access 警告".encode(),
        b"\x00\x01\x02\xfe\xff\x80\x81\x90\xaa\xbb\xcc",
    ],
    ids=["hello", "hello_lf", "hello_crlf", "unicode_utf8", "binary_non_utf8"],
)
def test_sha256_exact_byte_preservation_and_distinct_hashes(payload: bytes):
    """
    P0-3 Requirement:
    b"hello", b"hello\n", and b"hello\r\n" must have distinct hashes and preserve
    exact bytes without whitespace or line-ending stripping.
    """
    expected_hash = hashlib.sha256(payload).hexdigest()
    actual_hash = compute_sha256(payload)
    assert actual_hash == expected_hash

    # Verify hello vs hello\n vs hello\r\n hashes are distinct
    h1 = compute_sha256(b"hello")
    h2 = compute_sha256(b"hello\n")
    h3 = compute_sha256(b"hello\r\n")
    assert h1 != h2
    assert h2 != h3
    assert h1 != h3


def test_envelope_lossless_roundtrip_reconstruction():
    """
    P0-4 Requirement:
    original bytes -> SHA-256 -> envelope representation -> decode/reconstruct bytes -> SHA-256
    produces the exact same hash for both UTF-8 and non-UTF-8 binary data.
    """
    import base64

    from app.envelope.builder import build_envelope

    metadata = {
        "tenant_id": "test-tenant",
        "source_id": "test-source",
    }

    test_cases = [
        (b"hello", "utf-8"),
        (b"hello\n", "utf-8"),
        (b"hello\r\n", "utf-8"),
        ("CloudTrail: 🛡️ AssumeRole access 成功".encode(), "utf-8"),
        (b"\x00\xff\xfe\xfd\x80\x81\x82\x83\xde\xad\xbe\xef", "base64"),
    ]

    for original_bytes, expected_encoding in test_cases:
        orig_sha256 = compute_sha256(original_bytes)

        # 1. Build envelope
        envelope = build_envelope(
            raw_bytes=original_bytes,
            metadata=metadata,
            transport_protocol="http",
            transport_port=8000,
        )

        assert envelope.payload.encoding == expected_encoding
        assert envelope.integrity.hash == orig_sha256

        # 2. Reconstruct bytes from envelope data
        if envelope.payload.encoding == "base64":
            reconstructed_bytes = base64.b64decode(envelope.payload.data)
        elif envelope.payload.encoding == "utf-8":
            reconstructed_bytes = envelope.payload.data.encode("utf-8")
        else:
            raise ValueError(f"Unknown encoding: {envelope.payload.encoding}")

        # 3. Assert reconstructed bytes and SHA-256 are identical to original
        assert reconstructed_bytes == original_bytes
        reconstructed_sha256 = compute_sha256(reconstructed_bytes)
        assert reconstructed_sha256 == orig_sha256
