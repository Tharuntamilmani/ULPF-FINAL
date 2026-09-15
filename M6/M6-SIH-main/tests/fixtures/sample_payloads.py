"""Reusable sample payloads for contract and API tests."""

RAW_EVENT = {
    "envelope_id": "550e8400-e29b-41d4-a716-446655440000",
    "source_id": "cisco-fw-01",
    "tenant_id": "demo-tenant",
    "received_at": "2026-01-01T00:00:00Z",
    "transport": "udp",
    "protocol": "syslog",
    "parser_id": "parser-cisco-asa",
    "raw_payload": "Jan 1 00:00:00 fw01 %ASA-6-302013: Built outbound TCP ...",
    "byte_size": 80,
}

UES_V1 = {
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

HEALTH_RESPONSE_HEALTHY = {
    "service": "m1-ingestion",
    "status": "HEALTHY",
    "version": "1.0.0",
    "uptime_seconds": 3600.0,
    "timestamp": "2026-01-01T00:00:00Z",
}

HEALTH_RESPONSE_UNAVAILABLE = {
    "service": "m1-ingestion",
    "status": "UNAVAILABLE",
    "timestamp": "2026-01-01T00:00:00Z",
}
