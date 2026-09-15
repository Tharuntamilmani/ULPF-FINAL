"""RFC 8785 JSON Canonicalization Scheme (JCS) Implementation.

Provides deterministic, byte-exact serialization for cryptographic hashing.
Complies with RFC 8785:
- UTF-8 encoding
- Strict Unicode NFC normalization
- Lexicographical sorting of object keys by UTF-16 code units
- No extraneous whitespace
- Deterministic IEEE 754 float formatting
"""

import math
import unicodedata
from typing import Any


def _encode_string(s: str) -> str:
    """Normalize string to NFC and escape per RFC 8785 §3.2.2.2."""
    s_norm = unicodedata.normalize("NFC", s)
    out: list[str] = ['"']
    for char in s_norm:
        cp = ord(char)
        if char == '"':
            out.append(r"\"")
        elif char == "\\":
            out.append(r"\\")
        elif char == "\b":
            out.append(r"\b")
        elif char == "\f":
            out.append(r"\f")
        elif char == "\n":
            out.append(r"\n")
        elif char == "\r":
            out.append(r"\r")
        elif char == "\t":
            out.append(r"\t")
        elif cp < 0x20:
            out.append(f"\\u{cp:04x}")
        else:
            out.append(char)
    out.append('"')
    return "".join(out)


def _encode_number(n: int | float) -> str:
    """Format integer or float per RFC 8785 §3.2.2.3 and ECMAScript 6 standard."""
    if isinstance(n, int) and not isinstance(n, bool):
        return str(n)

    # Float handling
    if math.isnan(n) or math.isinf(n):
        raise ValueError(f"NaN and Infinity are not permitted in RFC 8785 canonical JSON: {n}")

    # Check for -0.0
    if n == 0.0:
        return "0"

    # Check if float is exact integer
    if n.is_integer() and abs(n) < 1e21:
        return str(int(n))

    # Standard 15-17 significant digits ECMAScript number representation
    # Format using standard Python representation then normalize exponent
    s = f"{n:.16g}"
    # Python format might use e+05 or e-05; ECMAScript uses e+5 (or e5) and e-5
    if "e" in s or "E" in s:
        mantissa, exp = s.lower().split("e")
        exp_int = int(exp)
        return f"{mantissa}e{exp_int}"
    return s


def _utf16_sort_key(s: str) -> tuple[int, ...]:
    """Compute sort key corresponding to UTF-16 code units per RFC 8785 §3.2.3."""
    norm_s = unicodedata.normalize("NFC", s)
    code_units: list[int] = []
    for char in norm_s:
        cp = ord(char)
        if cp <= 0xFFFF:
            code_units.append(cp)
        else:
            # Surrogate pair representation
            cp -= 0x10000
            high_surrogate = 0xD800 + (cp >> 10)
            low_surrogate = 0xDC00 + (cp & 0x3FF)
            code_units.extend((high_surrogate, low_surrogate))
    return tuple(code_units)


def canonicalize_to_str(obj: Any) -> str:
    """Recursively serialize a Python data structure into RFC 8785 canonical JSON string."""
    if obj is None:
        return "null"
    if isinstance(obj, bool):
        return "true" if obj else "false"
    if isinstance(obj, int | float):
        return _encode_number(obj)
    if isinstance(obj, str):
        return _encode_string(obj)
    if isinstance(obj, list | tuple):
        items = [canonicalize_to_str(item) for item in obj]
        return "[" + ",".join(items) + "]"
    if isinstance(obj, dict):
        # Sort keys lexicographically by UTF-16 code units
        sorted_keys = sorted(obj.keys(), key=_utf16_sort_key)
        pairs: list[str] = []
        for k in sorted_keys:
            if not isinstance(k, str):
                raise TypeError(f"Dictionary keys must be strings in RFC 8785: {k!r}")
            k_encoded = _encode_string(k)
            v_encoded = canonicalize_to_str(obj[k])
            pairs.append(f"{k_encoded}:{v_encoded}")
        return "{" + ",".join(pairs) + "}"
    if hasattr(obj, "model_dump"):
        return canonicalize_to_str(obj.model_dump(mode="json"))
    if hasattr(obj, "__dict__"):
        return canonicalize_to_str(vars(obj))

    raise TypeError(f"Unsupported data type for canonicalization: {type(obj).__name__}")


def canonicalize(obj: Any) -> bytes:
    """Serialize object to RFC 8785 canonical JSON UTF-8 byte stream."""
    return canonicalize_to_str(obj).encode("utf-8")
