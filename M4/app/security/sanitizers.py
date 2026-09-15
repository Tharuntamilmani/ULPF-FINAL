"""Sanitizers to prevent secret leakage in logs and diagnostics."""

import re
from typing import Any

SENSITIVE_KEYS = {
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "auth_token",
    "access_token",
    "bearer",
    "private_key",
}

BEARER_REGEX = re.compile(r"(bearer\s+)([a-zA-Z0-9_\-\.]+)", re.IGNORECASE)
API_KEY_REGEX = re.compile(
    r"(key|token|secret|password|pwd)=([a-zA-Z0-9_\-\.!@#$%^&*]+)", re.IGNORECASE
)


def sanitize_value(key: str, val: Any) -> Any:
    """Mask value if the key matches known sensitive keywords."""
    if not isinstance(key, str):
        return val

    key_clean = key.lower().replace("-", "_")
    if any(sensitive in key_clean for sensitive in SENSITIVE_KEYS):
        return "[REDACTED]"

    if isinstance(val, str):
        # Scrub inline bearer tokens or query param keys
        scrubbed = BEARER_REGEX.sub(r"\1[REDACTED]", val)
        scrubbed = API_KEY_REGEX.sub(r"\1=[REDACTED]", scrubbed)
        return scrubbed

    if isinstance(val, dict):
        return sanitize_dict(val)

    if isinstance(val, list):
        return [sanitize_value(key, item) for item in val]

    return val


def sanitize_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize a dictionary."""
    sanitized: dict[str, Any] = {}
    for k, v in d.items():
        sanitized[k] = sanitize_value(k, v)
    return sanitized
