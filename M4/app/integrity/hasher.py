"""Cryptographic hashing subsystem for ULPF M4."""

import hashlib
from typing import Any

from app.integrity.canonicalizer import canonicalize


def hash_bytes_sha256(data: bytes) -> str:
    """Compute SHA-256 digest of raw byte sequence."""
    return hashlib.sha256(data).hexdigest().lower()


def hash_canonical_sha256(obj: Any) -> str:
    """Compute SHA-256 digest of an object serialized via RFC 8785 canonical JSON."""
    canonical_bytes = canonicalize(obj)
    return hash_bytes_sha256(canonical_bytes)
