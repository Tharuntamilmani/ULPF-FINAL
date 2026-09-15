from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_and_metrics_unauthenticated():
    # Health check is unauthenticated
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "m2-parser"
    assert "registry_size" in data

    # Metrics is unauthenticated
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "ulpf_parser_events_total" in res.text


def test_parse_event_anonymous_rejected():
    # Anonymous request to /v1/parse must return 401
    payload = {
        "raw_event_id": "test_raw_001",
        "tenant_id": "tenant-a",
        "payload": "<189>Sep 12 04:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection",
    }
    res = client.post("/v1/parse", json=payload)
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]


def test_parse_event_invalid_key_rejected():
    payload = {
        "raw_event_id": "test_raw_001",
        "tenant_id": "tenant-a",
        "payload": "<189>Sep 12 04:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection",
    }
    res = client.post(
        "/v1/parse", json=payload, headers={"X-API-Key": "invalid-bogus-key"}
    )
    assert res.status_code == 401


def test_parse_event_insufficient_role_forbidden():
    # Analyst key does not have ingest role
    payload = {
        "raw_event_id": "test_raw_001",
        "tenant_id": "tenant-a",
        "payload": "<189>Sep 12 04:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection",
    }
    res = client.post(
        "/v1/parse", json=payload, headers={"X-API-Key": "tenant-a-analyst-key"}
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]


def test_parse_event_tenant_spoofing_forbidden():
    # Tenant A ingest key attempting to submit event for Tenant B
    payload = {
        "raw_event_id": "test_raw_spoof",
        "tenant_id": "tenant-b",
        "payload": "<189>Sep 12 04:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection",
    }
    res = client.post(
        "/v1/parse", json=payload, headers={"X-API-Key": "tenant-a-ingest-key"}
    )
    assert res.status_code == 403
    assert "cannot ingest for" in res.json()["detail"]


def test_parse_event_success_cisco_asa():
    payload = {
        "schema_version": "1.0.0",
        "raw_event_id": "raw_cisco_valid_001",
        "tenant_id": "tenant-a",
        "source_id": "cisco-asa-fw01",
        "transport": "syslog",
        "payload": "<189>Sep 12 04:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443",
    }
    res = client.post(
        "/v1/parse", json=payload, headers={"X-API-Key": "tenant-a-ingest-key"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["schema_version"] == "1.0.0"
    assert data["raw_event_id"] == "raw_cisco_valid_001"
    assert data["tenant_id"] == "tenant-a"
    assert data["source_id"] == "cisco-asa-fw01"
    assert data["status"] == "PARSED"
    assert data["parser"]["id"] == "parser-cisco-asa"
    assert data["fields"]["connection_id"] == 847392
    assert data["fields"]["srcip"] == "192.168.10.25"
    assert data["fields"]["dstip"] == "8.8.8.8"
    assert data["sha256"] is not None


def test_parse_unknown_event_returns_unparsed_status():
    # Unknown event must NOT invent token_0, token_1 fields
    payload = {
        "raw_event_id": "raw_unknown_001",
        "tenant_id": "tenant-a",
        "payload": "unrecognized raw binary gibberish 999 888 777",
    }
    res = client.post(
        "/v1/parse", json=payload, headers={"X-API-Key": "tenant-a-ingest-key"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "UNPARSED"
    assert data["fields"] == {}
    assert data["parser"]["id"] == "unparsed"
    assert "token_0" not in data["fields"]


def test_discover_unknown_event_endpoint():
    payload = {
        "raw_event_id": "disc_001",
        "payload": "user=admin action=login ip=10.0.0.1 port=22",
    }
    res = client.post(
        "/v1/parsers/discover",
        json=payload,
        headers={"X-API-Key": "tenant-a-analyst-key"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "detected_fields" in data
    assert "user" in data["detected_fields"]
    assert "suggestions" in data


def test_parser_studio_validate_and_register_api():
    # Test valid definition registration
    new_parser = {
        "id": "parser-custom-tenant-a",
        "name": "Tenant A Custom App Parser",
        "tenant_id": "tenant-a",
        "vendor": "CustomCorp",
        "product": "AppServer",
        "formats": ["syslog"],
        "version": "1.0.0",
        "patterns": ["^APP_LOG user=%{WORD:user} latency=%{INT:latency_ms}"],
    }
    res = client.post(
        "/v1/parsers/register",
        json=new_parser,
        headers={"X-API-Key": "tenant-a-admin-key"},
    )
    assert res.status_code == 200
    assert res.json()["id"] == "parser-custom-tenant-a"

    # Test parse with newly registered custom parser
    event_payload = {
        "raw_event_id": "custom_001",
        "tenant_id": "tenant-a",
        "payload": "APP_LOG user=bob latency=45",
    }
    res2 = client.post(
        "/v1/parse", json=event_payload, headers={"X-API-Key": "tenant-a-ingest-key"}
    )
    assert res2.status_code == 200
    assert res2.json()["fields"]["user"] == "bob"
    assert res2.json()["fields"]["latency_ms"] == 45


def test_register_parser_with_redos_rejected():
    malicious_parser = {
        "id": "parser-malicious-redos",
        "name": "Malicious Parser",
        "tenant_id": "tenant-a",
        "vendor": "Malicious",
        "product": "ReDoS",
        "formats": ["syslog"],
        "version": "1.0.0",
        "patterns": ["(a+)+$"],
    }
    res = client.post(
        "/v1/parsers/register",
        json=malicious_parser,
        headers={"X-API-Key": "tenant-a-admin-key"},
    )
    assert res.status_code == 422
    assert "violates ReDoS safety check" in res.json()["detail"]


def test_register_global_parser_by_tenant_forbidden():
    global_parser = {
        "id": "parser-fake-global",
        "name": "Fake Global",
        "tenant_id": "global",
        "vendor": "Global",
        "product": "Global",
        "formats": ["syslog"],
        "version": "1.0.0",
        "patterns": ["^test.*"],
    }
    res = client.post(
        "/v1/parsers/register",
        json=global_parser,
        headers={"X-API-Key": "tenant-a-admin-key"},
    )
    assert res.status_code == 422
    assert (
        "Non-system callers cannot register global baseline parsers"
        in res.json()["detail"]
    )


def test_parser_disable_enable_lifecycle_api():
    # Disable
    res = client.post(
        "/v1/parsers/parser-cisco-asa/disable",
        headers={"X-API-Key": "system-admin-token"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "disabled"

    # Enable
    res2 = client.post(
        "/v1/parsers/parser-cisco-asa/enable",
        headers={"X-API-Key": "system-admin-token"},
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "active"
