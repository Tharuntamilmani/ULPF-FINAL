import hashlib


def compute_sha256(raw_bytes: bytes) -> str:
    """
    Computes a SHA-256 hex digest over exact, untouched raw bytes.
    MUST be called on raw byte payloads before any decoding or transformation.
    """
    if not isinstance(raw_bytes, (bytes, bytearray)):
        raise TypeError(f"Expected bytes or bytearray, got {type(raw_bytes).__name__}")
    return hashlib.sha256(raw_bytes).hexdigest()
