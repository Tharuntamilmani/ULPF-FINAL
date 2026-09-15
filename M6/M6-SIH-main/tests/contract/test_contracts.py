"""
Contract compatibility tests.

Validates:
  1. All JSON schema files are valid
  2. Sample payloads pass against their schema
  3. Required fields — removing any required field fails validation
  4. Pipeline compatibility (M1 output → M2 input, etc.)
  5. Breaking-change detection (UES v2.0.0 requires severity)

These tests run WITHOUT any M1-M5 source code.
They operate only on JSON schemas and fixture payloads.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

CONTRACTS_DIR = Path(__file__).parents[2] / "contracts"


def load_schema(rel_path: str) -> dict[str, Any]:
    p = CONTRACTS_DIR / rel_path
    assert p.exists(), f"Contract schema not found: {p}"
    with open(p) as f:
        return json.load(f)


def validate(schema: dict, instance: dict) -> None:
    jsonschema.validate(instance=instance, schema=schema)


# ── Sample payloads ────────────────────────────────────────────────────────────

RAW_EVENT_VALID = {
    "envelope_id": "550e8400-e29b-41d4-a716-446655440000",
    "source_id": "cisco-fw-01",
    "tenant_id": "demo-tenant",
    "received_at": "2026-01-01T00:00:00Z",
    "transport": "udp",
    "protocol": "syslog",
    "parser_id": "parser-cisco-asa",
    "raw_payload": "Jan 1 00:00:00 fw01 %ASA-6-302013: ...",
    "byte_size": 64,
}

PARSED_EVENT_VALID = {
    "event_id": "evt-001",
    "envelope_id": "550e8400-e29b-41d4-a716-446655440000",
    "source_id": "cisco-fw-01",
    "tenant_id": "demo-tenant",
    "parsed_at": "2026-01-01T00:00:01Z",
    "parser_id": "parser-cisco-asa",
    "parser_version": "1.0.0",
    "fields": {
        "srcip": "192.168.1.10",
        "dstip": "10.0.0.1",
        "srcport": "54321",
        "dstport": "443",
        "action": "allow",
    },
}

UES_V1_VALID = {
    "event_id": "ues-001",
    "tenant_id": "demo-tenant",
    "timestamp": "2026-01-01T00:00:02Z",
    "schema_version": "1.0.0",
    "event": {
        "category": "network",
        "action": "allow",
        "outcome": "success",
        "severity": {"label": "low", "value": 2},
    },
    "source": {"ip": "192.168.1.10", "port": 54321},
    "destination": {"ip": "10.0.0.1", "port": 443},
    "observer": {"source_id": "cisco-fw-01", "parser_id": "parser-cisco-asa"},
}

UES_V2_VALID = {
    **UES_V1_VALID,
    "schema_version": "2.0.0",
    "event": {
        "category": "network",
        "action": "allow",
        "outcome": "success",
        "severity": {"value": 2, "label": "low"},  # required in v2
    },
}

UES_V2_MISSING_SEVERITY = {
    **UES_V1_VALID,
    "schema_version": "2.0.0",
    "event": {
        "category": "network",
        "action": "allow",
        # severity MISSING — should fail v2 validation
    },
}

ENRICHED_UES_VALID = {
    **UES_V1_VALID,
    "enrichment": {
        "threat_intel": {"is_known_bad_ip": False, "confidence": 0.1},
        "geo": {"source_country": "US", "source_lat": 37.7, "source_lon": -122.4},
        "enriched_at": "2026-01-01T00:00:03Z",
        "enricher_id": "enricher-m4",
    },
}

ROUTING_CONFIG_VALID = {
    "policy_id": "critical-security",
    "name": "Critical Security",
    "version": "1.0.0",
    "priority": 100,
    "is_enabled": True,
    "conditions": [
        {"field": "event.severity.value", "operator": ">=", "value": 4},
        {"field": "security.is_security_event", "operator": "==", "value": True},
    ],
    "destinations": ["siem", "data_lake"],
}

HEALTH_RESPONSE_VALID = {
    "service": "m1-ingestion",
    "status": "HEALTHY",
    "version": "1.0.0",
    "uptime_seconds": 3600.0,
    "timestamp": "2026-01-01T00:00:00Z",
}

REPLAY_REQUEST_VALID = {
    "replay_id": "rpl-001",
    "event_id": "evt-001",
    "source": "cisco-fw-01",
    "reason": "Parser bug fix — re-process event",
    "requested_by": "admin",
    "requested_at": "2026-01-01T00:00:00Z",
}

AUDIT_EVENT_VALID = {
    "id": "aud-001",
    "timestamp": "2026-01-01T00:00:00Z",
    "actor": "admin",
    "actor_role": "ADMINISTRATOR",
    "action": "SOURCE_CREATED",
    "resource_type": "source",
    "resource_id": "cisco-fw-01",
    "result": "SUCCESS",
}

CONFIG_UPDATE_VALID = {
    "event": "config_updated",
    "config_key": "sources",
    "version": 1704067200000,
    "timestamp": "2026-01-01T00:00:00Z",
}


# ── Tests: schema files exist and are valid JSON ───────────────────────────────


@pytest.mark.parametrize(
    "path",
    [
        "raw_event/v1/schema.json",
        "parsed_event/v1/schema.json",
        "ues/v1.0.0/schema.json",
        "ues/v1.1.0/schema.json",
        "ues/v2.0.0/schema.json",
        "enrichment/v1/schema.json",
        "routing/v1/schema.json",
        "health/v1/schema.json",
        "replay/v1/schema.json",
        "audit/v1/schema.json",
        "configuration/v1/schema.json",
    ],
)
def test_schema_file_exists_and_valid_json(path: str) -> None:
    schema = load_schema(path)
    assert isinstance(schema, dict)
    assert "$id" in schema or "title" in schema


# ── Tests: valid payloads pass ────────────────────────────────────────────────


def test_raw_event_valid() -> None:
    validate(load_schema("raw_event/v1/schema.json"), RAW_EVENT_VALID)


def test_parsed_event_valid() -> None:
    validate(load_schema("parsed_event/v1/schema.json"), PARSED_EVENT_VALID)


def test_ues_v1_valid() -> None:
    validate(load_schema("ues/v1.0.0/schema.json"), UES_V1_VALID)


def test_ues_v2_valid() -> None:
    validate(load_schema("ues/v2.0.0/schema.json"), UES_V2_VALID)


def test_enriched_ues_valid() -> None:
    validate(load_schema("enrichment/v1/schema.json"), ENRICHED_UES_VALID)


def test_routing_config_valid() -> None:
    validate(load_schema("routing/v1/schema.json"), ROUTING_CONFIG_VALID)


def test_health_response_valid() -> None:
    validate(load_schema("health/v1/schema.json"), HEALTH_RESPONSE_VALID)


def test_replay_request_valid() -> None:
    validate(load_schema("replay/v1/schema.json"), REPLAY_REQUEST_VALID)


def test_audit_event_valid() -> None:
    validate(load_schema("audit/v1/schema.json"), AUDIT_EVENT_VALID)


def test_config_update_valid() -> None:
    validate(load_schema("configuration/v1/schema.json"), CONFIG_UPDATE_VALID)


# ── Tests: required field removal fails validation ────────────────────────────


@pytest.mark.parametrize("missing_field", ["envelope_id", "source_id", "raw_payload"])
def test_raw_event_missing_required(missing_field: str) -> None:
    schema = load_schema("raw_event/v1/schema.json")
    payload = {k: v for k, v in RAW_EVENT_VALID.items() if k != missing_field}
    with pytest.raises(jsonschema.ValidationError):
        validate(schema, payload)


@pytest.mark.parametrize("missing_field", ["event_id", "fields"])
def test_parsed_event_missing_required(missing_field: str) -> None:
    schema = load_schema("parsed_event/v1/schema.json")
    payload = {k: v for k, v in PARSED_EVENT_VALID.items() if k != missing_field}
    with pytest.raises(jsonschema.ValidationError):
        validate(schema, payload)


# ── Tests: breaking-change detection ─────────────────────────────────────────


def test_ues_v2_requires_severity_breaking_change() -> None:
    """
    UES v2.0.0 requires event.severity — a BREAKING change from v1.0.0.
    An event that passes v1.0.0 validation FAILS v2.0.0 if severity is absent.
    """
    schema_v1 = load_schema("ues/v1.0.0/schema.json")
    schema_v2 = load_schema("ues/v2.0.0/schema.json")

    # Payload with no severity — valid in v1, invalid in v2
    payload_no_severity = {
        "event_id": "ues-002",
        "tenant_id": "demo",
        "timestamp": "2026-01-01T00:00:00Z",
        "schema_version": "1.0.0",
        "event": {"category": "network", "action": "allow"},
    }
    validate(schema_v1, payload_no_severity)  # passes v1
    with pytest.raises(jsonschema.ValidationError):
        # Must fail v2 (severity required)
        payload_v2 = {**payload_no_severity, "schema_version": "2.0.0"}
        validate(schema_v2, payload_v2)


def test_ues_v1_and_v1_1_backward_compatible() -> None:
    """v1.0.0 payload must validate against v1.1.0 (backward compatible)."""
    schema_v1_1 = load_schema("ues/v1.1.0/schema.json")
    # v1 payload should still pass v1.1.0
    validate(schema_v1_1, {**UES_V1_VALID, "schema_version": "1.1.0"})


# ── Tests: pipeline contract compatibility ────────────────────────────────────


def test_m1_output_satisfies_m2_input() -> None:
    """M1 raw_event output fields must satisfy M2 parsed_event input envelope_id reference."""
    raw = RAW_EVENT_VALID
    parsed = PARSED_EVENT_VALID
    # envelope_id must flow from M1 → M2
    assert raw["envelope_id"] == parsed["envelope_id"]
    assert raw["source_id"] == parsed["source_id"]
    assert raw["tenant_id"] == parsed["tenant_id"]


def test_m2_output_satisfies_m3_input() -> None:
    """M2 parsed_event output must provide fields M3 uses for normalisation."""
    parsed = PARSED_EVENT_VALID
    assert "fields" in parsed
    assert "source_id" in parsed
    assert "parser_id" in parsed


def test_m3_output_satisfies_m4_input() -> None:
    """M3 UES output fields must be present for M4 enrichment."""
    ues = UES_V1_VALID
    assert "event_id" in ues
    assert "source" in ues
    assert "event" in ues


def test_m4_output_satisfies_m5_input() -> None:
    """M4 enriched UES must have enrichment block for M5 routing."""
    enriched = ENRICHED_UES_VALID
    schema = load_schema("enrichment/v1/schema.json")
    validate(schema, enriched)
    assert "enrichment" in enriched


def test_health_response_unavailable_status() -> None:
    """UNAVAILABLE is a valid health status per contract."""
    schema = load_schema("health/v1/schema.json")
    validate(schema, {**HEALTH_RESPONSE_VALID, "status": "UNAVAILABLE"})


def test_health_response_rejects_unknown_status() -> None:
    """Unknown health status must fail contract validation."""
    schema = load_schema("health/v1/schema.json")
    with pytest.raises(jsonschema.ValidationError):
        validate(schema, {**HEALTH_RESPONSE_VALID, "status": "PARTIALLY_HEALTHY"})
