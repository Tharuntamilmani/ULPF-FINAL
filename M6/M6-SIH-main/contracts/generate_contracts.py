"""
Generate all ULPF contract JSON schema files.
Run: python contracts/generate_contracts.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

BASE = Path(__file__).parent

CONTRACTS: dict[str, dict] = {
    "raw_event/v1/schema": {
        "$id": "ulpf:contracts:raw_event:v1",
        "title": "RawEventEnvelope",
        "description": "M1 output / M2 input contract. M6 distributes; never processes events.",
        "type": "object",
        "required": ["envelope_id", "source_id", "tenant_id", "received_at", "transport", "raw_payload"],
        "additionalProperties": False,
        "properties": {
            "envelope_id":  {"type": "string"},
            "source_id":    {"type": "string", "minLength": 1},
            "tenant_id":    {"type": "string", "minLength": 1},
            "received_at":  {"type": "string"},
            "transport":    {"type": "string", "enum": ["udp", "tcp", "http", "https", "file", "kafka"]},
            "protocol":     {"type": "string"},
            "parser_id":    {"type": "string"},
            "raw_payload":  {"type": "string"},
            "encoding":     {"type": "string", "default": "utf-8"},
            "byte_size":    {"type": "integer", "minimum": 0},
            "collector_id": {"type": "string"},
            "tags":         {"type": "array", "items": {"type": "string"}},
            "metadata":     {"type": "object"},
        },
    },
    "parsed_event/v1/schema": {
        "$id": "ulpf:contracts:parsed_event:v1",
        "title": "ParsedEvent",
        "description": "M2 output / M3 input contract.",
        "type": "object",
        "required": ["event_id", "envelope_id", "source_id", "tenant_id", "parsed_at", "parser_id", "fields"],
        "additionalProperties": False,
        "properties": {
            "event_id":     {"type": "string"},
            "envelope_id":  {"type": "string"},
            "source_id":    {"type": "string"},
            "tenant_id":    {"type": "string"},
            "parsed_at":    {"type": "string"},
            "parser_id":    {"type": "string"},
            "parser_version": {"type": "string"},
            "fields":       {"type": "object", "description": "Flat key/value parsed fields"},
            "parse_errors": {"type": "array", "items": {"type": "string"}},
            "raw_ref":      {"type": "string", "description": "Reference back to raw envelope"},
        },
    },
    "ues/v1.0.0/schema": {
        "$id": "ulpf:contracts:ues:v1.0.0",
        "title": "UniversalEventSchema v1.0.0",
        "description": "M3 output / M4 input contract. Normalised event format.",
        "type": "object",
        "required": ["event_id", "tenant_id", "timestamp", "event"],
        "properties": {
            "event_id":     {"type": "string"},
            "tenant_id":    {"type": "string"},
            "timestamp":    {"type": "string"},
            "schema_version": {"type": "string", "const": "1.0.0"},
            "event": {
                "type": "object",
                "required": ["category", "action"],
                "properties": {
                    "category":   {"type": "string"},
                    "action":     {"type": "string"},
                    "outcome":    {"type": "string", "enum": ["success", "failure", "unknown"]},
                    "severity":   {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "value": {"type": "integer", "minimum": 0, "maximum": 10},
                        },
                    },
                },
            },
            "source": {
                "type": "object",
                "properties": {
                    "ip":   {"type": "string"},
                    "port": {"type": "integer"},
                    "host": {"type": "string"},
                },
            },
            "destination": {
                "type": "object",
                "properties": {
                    "ip":   {"type": "string"},
                    "port": {"type": "integer"},
                    "host": {"type": "string"},
                },
            },
            "network": {
                "type": "object",
                "properties": {
                    "protocol":  {"type": "string"},
                    "transport": {"type": "string"},
                    "direction": {"type": "string"},
                    "bytes":     {"type": "integer"},
                },
            },
            "security": {
                "type": "object",
                "properties": {
                    "is_security_event": {"type": "boolean"},
                    "threat_indicators": {"type": "array", "items": {"type": "string"}},
                },
            },
            "observer": {
                "type": "object",
                "properties": {
                    "source_id":  {"type": "string"},
                    "parser_id":  {"type": "string"},
                    "vendor":     {"type": "string"},
                    "product":    {"type": "string"},
                },
            },
            "raw_ref":    {"type": "string"},
            "tags":       {"type": "array", "items": {"type": "string"}},
            "labels":     {"type": "object"},
        },
    },
    "ues/v1.1.0/schema": {
        "$id": "ulpf:contracts:ues:v1.1.0",
        "title": "UniversalEventSchema v1.1.0",
        "description": "UES v1.1.0 — adds user and process fields (backward compatible with v1.0.0).",
        "type": "object",
        "required": ["event_id", "tenant_id", "timestamp", "event"],
        "properties": {
            "event_id":     {"type": "string"},
            "tenant_id":    {"type": "string"},
            "timestamp":    {"type": "string"},
            "schema_version": {"type": "string", "const": "1.1.0"},
            "event":        {"type": "object"},
            "source":       {"type": "object"},
            "destination":  {"type": "object"},
            "network":      {"type": "object"},
            "security":     {"type": "object"},
            "observer":     {"type": "object"},
            "user": {
                "type": "object",
                "properties": {
                    "name":   {"type": "string"},
                    "id":     {"type": "string"},
                    "domain": {"type": "string"},
                },
            },
            "process": {
                "type": "object",
                "properties": {
                    "name":       {"type": "string"},
                    "pid":        {"type": "integer"},
                    "executable": {"type": "string"},
                    "args":       {"type": "array", "items": {"type": "string"}},
                },
            },
            "raw_ref": {"type": "string"},
            "tags":    {"type": "array", "items": {"type": "string"}},
            "labels":  {"type": "object"},
        },
    },
    "ues/v2.0.0/schema": {
        "$id": "ulpf:contracts:ues:v2.0.0",
        "title": "UniversalEventSchema v2.0.0",
        "description": "UES v2.0.0 — breaking change: event.severity is now required; adds geo field.",
        "type": "object",
        "required": ["event_id", "tenant_id", "timestamp", "event", "schema_version"],
        "properties": {
            "event_id":       {"type": "string"},
            "tenant_id":      {"type": "string"},
            "timestamp":      {"type": "string"},
            "schema_version": {"type": "string", "const": "2.0.0"},
            "event": {
                "type": "object",
                "required": ["category", "action", "severity"],
                "properties": {
                    "category": {"type": "string"},
                    "action":   {"type": "string"},
                    "outcome":  {"type": "string"},
                    "severity": {
                        "type": "object",
                        "required": ["value"],
                        "properties": {
                            "label": {"type": "string"},
                            "value": {"type": "integer", "minimum": 0, "maximum": 10},
                        },
                    },
                },
            },
            "source":      {"type": "object"},
            "destination": {"type": "object"},
            "network":     {"type": "object"},
            "security":    {"type": "object"},
            "observer":    {"type": "object"},
            "user":        {"type": "object"},
            "process":     {"type": "object"},
            "geo": {
                "type": "object",
                "properties": {
                    "source_country":      {"type": "string"},
                    "destination_country": {"type": "string"},
                },
            },
            "raw_ref": {"type": "string"},
            "tags":    {"type": "array", "items": {"type": "string"}},
            "labels":  {"type": "object"},
        },
    },
    "enrichment/v1/schema": {
        "$id": "ulpf:contracts:enrichment:v1",
        "title": "EnrichedUES",
        "description": "M4 output / M5 input contract.",
        "type": "object",
        "required": ["event_id", "tenant_id", "timestamp", "event", "enrichment"],
        "properties": {
            "event_id":     {"type": "string"},
            "tenant_id":    {"type": "string"},
            "timestamp":    {"type": "string"},
            "schema_version": {"type": "string"},
            "event":        {"type": "object"},
            "source":       {"type": "object"},
            "destination":  {"type": "object"},
            "network":      {"type": "object"},
            "security":     {"type": "object"},
            "enrichment": {
                "type": "object",
                "properties": {
                    "threat_intel": {
                        "type": "object",
                        "properties": {
                            "is_known_bad_ip": {"type": "boolean"},
                            "threat_categories": {"type": "array", "items": {"type": "string"}},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        },
                    },
                    "geo": {
                        "type": "object",
                        "properties": {
                            "source_city":    {"type": "string"},
                            "source_country": {"type": "string"},
                            "source_lat":     {"type": "number"},
                            "source_lon":     {"type": "number"},
                        },
                    },
                    "asset": {
                        "type": "object",
                        "properties": {
                            "hostname":       {"type": "string"},
                            "owner":          {"type": "string"},
                            "criticality":    {"type": "string"},
                        },
                    },
                    "enriched_at":  {"type": "string"},
                    "enricher_id":  {"type": "string"},
                },
            },
        },
    },
    "routing/v1/schema": {
        "$id": "ulpf:contracts:routing:v1",
        "title": "RoutingConfig",
        "description": "Policy config distributed by M6 to M5 via Redis.",
        "type": "object",
        "required": ["policy_id", "version", "conditions", "destinations"],
        "properties": {
            "policy_id":    {"type": "string"},
            "name":         {"type": "string"},
            "version":      {"type": "string"},
            "priority":     {"type": "integer"},
            "is_enabled":   {"type": "boolean"},
            "conditions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["field", "operator", "value"],
                    "properties": {
                        "field":    {"type": "string"},
                        "operator": {"type": "string"},
                        "value":    {},
                    },
                },
            },
            "destinations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "e.g. siem, data_lake, ai_stream",
            },
        },
    },
    "health/v1/schema": {
        "$id": "ulpf:contracts:health:v1",
        "title": "HealthResponse",
        "description": "Standard health response all M1-M5 services must expose at GET /health.",
        "type": "object",
        "required": ["service", "status"],
        "properties": {
            "service":    {"type": "string"},
            "status":     {"type": "string", "enum": ["HEALTHY", "DEGRADED", "UNHEALTHY", "UNAVAILABLE", "UNKNOWN"]},
            "version":    {"type": "string"},
            "uptime_seconds": {"type": "number"},
            "checks":     {"type": "object"},
            "timestamp":  {"type": "string"},
        },
    },
    "replay/v1/schema": {
        "$id": "ulpf:contracts:replay:v1",
        "title": "ReplayRequest",
        "description": "Kafka message published by M6 on ulpf.replay topic.",
        "type": "object",
        "required": ["replay_id", "event_id", "requested_by", "requested_at"],
        "properties": {
            "replay_id":     {"type": "string"},
            "event_id":      {"type": "string"},
            "source":        {"type": "string"},
            "reason":        {"type": "string"},
            "requested_by":  {"type": "string"},
            "requested_at":  {"type": "string"},
            "timestamp":     {"type": "string"},
        },
    },
    "audit/v1/schema": {
        "$id": "ulpf:contracts:audit:v1",
        "title": "AuditEvent",
        "description": "Audit log entry structure for all M6 administrative actions.",
        "type": "object",
        "required": ["id", "timestamp", "actor", "action", "resource_type", "result"],
        "properties": {
            "id":            {"type": "string"},
            "timestamp":     {"type": "string"},
            "actor":         {"type": "string"},
            "actor_role":    {"type": "string"},
            "action":        {"type": "string"},
            "resource_type": {"type": "string"},
            "resource_id":   {"type": "string"},
            "version":       {"type": "string"},
            "before_state":  {"type": "object"},
            "after_state":   {"type": "object"},
            "reason":        {"type": "string"},
            "result":        {"type": "string", "enum": ["SUCCESS", "FAILURE", "PARTIAL"]},
            "request_id":    {"type": "string"},
        },
    },
    "configuration/v1/schema": {
        "$id": "ulpf:contracts:configuration:v1",
        "title": "ConfigurationUpdate",
        "description": "Kafka message published by M6 on ulpf.m6.config.updates.",
        "type": "object",
        "required": ["event", "config_key", "version", "timestamp"],
        "properties": {
            "event":      {"type": "string", "const": "config_updated"},
            "config_key": {"type": "string", "enum": ["sources", "parsers", "schemas", "mappings", "policies"]},
            "version":    {"type": "integer"},
            "timestamp":  {"type": "string"},
        },
    },
}


def generate() -> None:
    for rel_path, schema in CONTRACTS.items():
        out_path = BASE / (rel_path + ".json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)
        print(f"  Written: {out_path.relative_to(BASE.parent)}")
    print(f"\nGenerated {len(CONTRACTS)} contract schemas.")


if __name__ == "__main__":
    generate()
