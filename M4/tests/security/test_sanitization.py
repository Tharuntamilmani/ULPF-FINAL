"""Security tests for credential scrubbing and log sanitization."""

import json

from app.observability.logging import StructuredJsonFormatter
from app.security.sanitizers import sanitize_dict, sanitize_value


def test_sanitize_sensitive_dictionary_keys() -> None:
    """Ensure sensitive key values are masked with [REDACTED]."""
    payload = {
        "user_id": "usr-123",
        "password": "SuperSecretPassword123!",
        "api_key": "m4-secret-key-abcdef",
        "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "safe_counter": 42,
    }
    sanitized = sanitize_dict(payload)
    assert sanitized["user_id"] == "usr-123"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["authorization"] == "[REDACTED]"
    assert sanitized["safe_counter"] == 42


def test_sanitize_inline_bearer_and_token_strings() -> None:
    """Ensure bearer tokens embedded within benign field values are masked."""
    val = "Authentication header was Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 passed in header"
    scrubbed = sanitize_value("header_log", val)
    assert "Bearer [REDACTED]" in scrubbed
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in scrubbed


def test_sanitize_recursive_nested_payload() -> None:
    """Ensure deeply nested structures are thoroughly sanitized."""
    nested = {
        "level1": {
            "level2": {
                "secret_token": "hidden_secret",
                "normal": "value",
            },
            "token_list": ["item1", "secret=mytoken123"],
        }
    }
    sanitized = sanitize_dict(nested)
    assert sanitized["level1"]["level2"]["secret_token"] == "[REDACTED]"
    assert sanitized["level1"]["level2"]["normal"] == "value"


def test_structured_json_formatter_masks_secrets() -> None:
    """Verify StructuredJsonFormatter applies sanitization to emitted log messages."""
    import logging

    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="User authentication with password=secretPassword123 failed",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    parsed = json.loads(formatted)
    assert parsed["level"] == "INFO"
    # Ensure raw secretPassword123 is redacted
    assert "secretPassword123" not in formatted
