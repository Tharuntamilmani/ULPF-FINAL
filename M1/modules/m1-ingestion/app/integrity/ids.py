import os
import time
import uuid


def generate_uuidv7() -> str:
    """
    Generates a time-sortable RFC 9562 compliant UUIDv7 string.
    Structure (128 bits total):
    - 48 bits: Unix timestamp in milliseconds
    - 4 bits: Version 7 (0b0111)
    - 12 bits: Pseudo-random data (rand_a)
    - 2 bits: Variant 2 (0b10 - RFC 9562)
    - 62 bits: Pseudo-random data (rand_b)
    """
    timestamp_ms = int(time.time() * 1000)
    rand_bytes = os.urandom(10)

    raw_bytes = bytearray(16)
    # 48-bit timestamp (ms)
    raw_bytes[0:6] = timestamp_ms.to_bytes(6, byteorder="big")
    # 4-bit version (7) + 12-bit rand_a
    raw_bytes[6] = (0x70) | (rand_bytes[0] & 0x0F)
    raw_bytes[7] = rand_bytes[1]
    # 2-bit variant (0b10) + upper 6 bits of rand_b
    raw_bytes[8] = (0x80) | (rand_bytes[2] & 0x3F)
    # remaining rand_b
    raw_bytes[9:16] = rand_bytes[3:10]

    return str(uuid.UUID(bytes=bytes(raw_bytes)))
