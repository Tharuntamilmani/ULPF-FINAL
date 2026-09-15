"""Structured JSON logging with security sanitization for ULPF M4."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.security.sanitizers import sanitize_dict


class StructuredJsonFormatter(logging.Formatter):
    """JSON log formatter that enforces structured schema and redacts secrets."""

    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include custom extra fields if attached
        if hasattr(record, "event_id"):
            data["event_id"] = record.event_id
        if hasattr(record, "tenant_id"):
            data["tenant_id"] = record.tenant_id
        if hasattr(record, "provider_id"):
            data["provider_id"] = record.provider_id
        if hasattr(record, "status"):
            data["status"] = record.status
        if hasattr(record, "duration_ms"):
            data["duration_ms"] = record.duration_ms
        if hasattr(record, "error_type"):
            data["error_type"] = record.error_type

        # Sanitize entire log record before output
        sanitized = sanitize_dict(data)
        return json.dumps(sanitized)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure and return the root M4 logger."""
    logger = logging.getLogger("ulpf.m4")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)

    return logger
