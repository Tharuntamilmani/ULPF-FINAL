"""Security tests for input tampering, prototype pollution, and adversarial injection."""

import pytest

from app.contracts.canonical_event import CanonicalEvent
from app.errors.exceptions import InvalidEventError, ProviderResponseError
from app.models.common import EnrichmentStatus
from app.providers.base import ProviderOutput
from app.validation.input_validator import InputValidator
from app.validation.result_validator import ResultValidator


def test_result_validator_rejects_prototype_pollution() -> None:
    """Ensure attempts to inject __proto__ or constructor are blocked."""
    bad_output = ProviderOutput(
        status=EnrichmentStatus.SUCCESS,
        data={"__proto__": {"polluted": True}},
    )
    with pytest.raises(ProviderResponseError, match="forbidden key name"):
        ResultValidator.validate_output("attacker-provider", bad_output)


def test_result_validator_rejects_overwriting_root_canonical_keys() -> None:
    """Ensure provider outputs cannot return root fields like 'event' or 'integrity'."""
    bad_output = ProviderOutput(
        status=EnrichmentStatus.SUCCESS,
        data={"event": {"id": "HIJACKED"}},
    )
    with pytest.raises(ProviderResponseError, match="forbidden key name"):
        ResultValidator.validate_output("attacker-provider", bad_output)


def test_result_validator_rejects_non_dict_data() -> None:
    """Ensure non-dict provider payload is rejected."""
    bad_output = ProviderOutput(
        status=EnrichmentStatus.SUCCESS,
        data={"ok": 1},
    )
    # Force mutation of data to invalid type
    object.__setattr__(bad_output, "data", "not-a-dict")
    with pytest.raises(ProviderResponseError, match="returned non-dict data"):
        ResultValidator.validate_output("bad-provider", bad_output)


def test_input_validator_rejects_empty_ids(sample_canonical_event: CanonicalEvent) -> None:
    """Verify input validator rejects empty event.id."""
    sample_canonical_event.event.id = "   "
    with pytest.raises(InvalidEventError, match="event.id is required"):
        InputValidator.validate_event(sample_canonical_event)


def test_input_validator_rejects_invalid_timestamp(sample_canonical_event: CanonicalEvent) -> None:
    """Verify input validator rejects invalid timestamps."""
    sample_canonical_event.event.timestamp = "not-a-timestamp"
    with pytest.raises(InvalidEventError, match="Invalid ISO 8601 timestamp"):
        InputValidator.validate_event(sample_canonical_event)


def test_input_validator_sql_injection_strings_treated_as_pure_data(
    sample_canonical_event: CanonicalEvent,
) -> None:
    """Ensure SQL / Command injection strings in fields are safely validated without execution."""
    sample_canonical_event.event.kind = "'; DROP TABLE events; --"
    sample_canonical_event.source.ip = "10.100.1.5"
    validated = InputValidator.validate_event(sample_canonical_event)
    assert validated.event.kind == "'; DROP TABLE events; --"
