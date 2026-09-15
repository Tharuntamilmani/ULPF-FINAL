"""Unit tests for RFC 8785 JSON Canonicalization Scheme (JCS)."""

import pytest

from app.integrity.canonicalizer import canonicalize, canonicalize_to_str


def test_canonicalize_primitive_types() -> None:
    """Test standard scalar primitives serialization."""
    assert canonicalize_to_str(None) == "null"
    assert canonicalize_to_str(True) == "true"
    assert canonicalize_to_str(False) == "false"
    assert canonicalize_to_str(42) == "42"
    assert canonicalize_to_str(-99) == "-99"
    assert canonicalize_to_str(0) == "0"


def test_canonicalize_string_escaping() -> None:
    """Test RFC 8785 mandatory string escaping."""
    assert canonicalize_to_str("hello") == '"hello"'
    assert canonicalize_to_str('a"b\\c') == r'"a\"b\\c"'
    assert canonicalize_to_str("line1\nline2") == r'"line1\nline2"'
    assert canonicalize_to_str("tab\tchar") == r'"tab\tchar"'
    assert canonicalize_to_str("\u0000") == r'"\u0000"'
    assert canonicalize_to_str("\u001f") == r'"\u001f"'


def test_canonicalize_unicode_nfc_normalization() -> None:
    """Verify Unicode NFC composition during canonicalization."""
    # 'e' + combining acute accent (NFD) vs 'é' precomposed (NFC)
    decomposed = "e\u0301"
    composed = "\u00e9"
    assert canonicalize_to_str(decomposed) == canonicalize_to_str(composed)


def test_canonicalize_lexicographical_key_sorting() -> None:
    """Verify that dictionary keys are sorted lexicographically by UTF-16 code units."""
    dict1 = {"z": 1, "a": 2, "m": 3}
    dict2 = {"a": 2, "m": 3, "z": 1}
    assert canonicalize_to_str(dict1) == '{"a":2,"m":3,"z":1}'
    assert canonicalize_to_str(dict1) == canonicalize_to_str(dict2)


def test_canonicalize_nested_structures() -> None:
    """Verify recursive sorting in nested objects and arrays."""
    nested = {
        "outer_b": [{"b": 1, "a": 2}],
        "outer_a": {"y": "val", "x": None},
    }
    expected = '{"outer_a":{"x":null,"y":"val"},"outer_b":[{"a":2,"b":1}]}'
    assert canonicalize_to_str(nested) == expected


def test_canonicalize_floats_and_integers() -> None:
    """Verify IEEE 754 number representation."""
    assert canonicalize_to_str(100.0) == "100"
    assert canonicalize_to_str(0.0) == "0"
    assert canonicalize_to_str(-0.0) == "0"
    assert canonicalize_to_str(3.14159) == "3.14159"


def test_canonicalize_disallows_nan_and_infinity() -> None:
    """Ensure NaN and Infinity are strictly rejected."""
    with pytest.raises(ValueError, match="NaN and Infinity"):
        canonicalize_to_str(float("nan"))
    with pytest.raises(ValueError, match="NaN and Infinity"):
        canonicalize_to_str(float("inf"))


def test_canonicalize_returns_utf8_bytes() -> None:
    """Ensure canonicalize() produces exact UTF-8 byte stream."""
    data = {"name": "Antigravity", "level": 100}
    b = canonicalize(data)
    assert isinstance(b, bytes)
    assert b == b'{"level":100,"name":"Antigravity"}'


def test_canonicalize_determinism_100_runs() -> None:
    """Verify byte-exact determinism across 100 repeated serialization passes."""
    data = {
        "event_id": "EVT-8821",
        "nested": {"z": 100, "b": [1, 2, 3], "a": "hello"},
        "flag": True,
        "score": 98.75,
    }
    baseline = canonicalize(data)
    for _ in range(100):
        assert canonicalize(data) == baseline
