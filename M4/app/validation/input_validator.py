"""Canonical event input validation for ULPF M4."""

from datetime import datetime
from typing import Any

from app.contracts.canonical_event import CanonicalEvent
from app.errors.exceptions import InvalidEventError

SUPPORTED_SCHEMAS = {"ues.v1", "1.0.0"}


class InputValidator:
    """Validates that incoming events strictly conform to canonical UES contract."""

    @classmethod
    def validate_event(cls, event: CanonicalEvent | dict[str, Any]) -> CanonicalEvent:
        """Validate canonical event or raise InvalidEventError.

        Does NOT attempt silent repairs.
        """
        if isinstance(event, dict):
            try:
                canonical = CanonicalEvent.model_validate(event)
            except Exception as e:
                raise InvalidEventError(f"Event failed canonical model validation: {e}") from e
        elif isinstance(event, CanonicalEvent):
            canonical = event
        else:
            raise InvalidEventError(f"Unsupported event payload type: {type(event).__name__}")

        if canonical.schema_version not in SUPPORTED_SCHEMAS:
            raise InvalidEventError(
                f"Unsupported schema version '{canonical.schema_version}'. Supported: {SUPPORTED_SCHEMAS}"
            )

        if not canonical.event.id or not canonical.event.id.strip():
            raise InvalidEventError("event.id is required and cannot be empty")

        if not canonical.provenance.raw_event_id or not canonical.provenance.raw_event_id.strip():
            raise InvalidEventError("provenance.raw_event_id is required and cannot be empty")

        if not canonical.tenant.tenant_id or not canonical.tenant.tenant_id.strip():
            raise InvalidEventError("tenant.tenant_id is required and cannot be empty")

        # Validate timestamp parseability
        try:
            datetime.fromisoformat(canonical.event.timestamp)
        except (ValueError, TypeError) as e:
            raise InvalidEventError(
                f"Invalid ISO 8601 timestamp '{canonical.event.timestamp}': {e}"
            ) from e

        return canonical
