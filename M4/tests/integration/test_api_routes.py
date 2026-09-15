"""Integration tests for FastAPI endpoints."""

from fastapi.testclient import TestClient

from app.contracts.canonical_event import CanonicalEvent
from app.integrity.verifier import calculate_integrity


def test_api_health_endpoint(test_client: TestClient) -> None:
    """Verify /health liveness probe."""
    resp = test_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
    assert resp.json()["module"] == "M4"


def test_api_ready_endpoint(test_client: TestClient) -> None:
    """Verify /ready readiness probe."""
    resp = test_client.get("/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["providers_registered"] >= 3


def test_api_metrics_endpoint(test_client: TestClient) -> None:
    """Verify Prometheus /metrics exposition endpoint."""
    resp = test_client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "m4_events_received_total" in text
    assert "m4_events_enriched_total" in text


def test_api_list_providers(test_client: TestClient) -> None:
    """Verify GET /v1/providers lists registered metadata."""
    resp = test_client.get("/v1/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    provider_ids = [p["provider_id"] for p in data]
    assert "asset-local-cmdb" in provider_ids
    assert "geoip-local-db" in provider_ids
    assert "threat-intel-local" in provider_ids


def test_api_get_configuration(test_client: TestClient) -> None:
    """Verify GET /v1/configuration returns active config."""
    resp = test_client.get("/v1/configuration")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "1.0.0"
    assert data["state"] == "active"


def test_api_post_enrich_success(
    test_client: TestClient, sample_canonical_event: CanonicalEvent
) -> None:
    """Verify POST /v1/enrich successfully enriches a canonical event."""
    payload = {
        "event": sample_canonical_event.model_dump(mode="json"),
        "options": {},
    }
    resp = test_client.post("/v1/enrich", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert "integrity" in data
    assert len(data["provenance"]) >= 3


def test_api_post_enrich_invalid_event(test_client: TestClient) -> None:
    """Verify POST /v1/enrich rejects invalid schema event with 400 Bad Request."""
    payload = {
        "event": {
            "schema_version": "unsupported.v9",
            "event": {"id": "123", "timestamp": "invalid-time"},
        }
    }
    resp = test_client.post("/v1/enrich", json=payload)
    assert resp.status_code in (400, 422)


def test_api_post_verify_integrity(
    test_client: TestClient, sample_canonical_event: CanonicalEvent
) -> None:
    """Verify POST /v1/verify passes for valid event and fails for tampered event."""
    # Compute digest
    meta = calculate_integrity(sample_canonical_event)
    sample_canonical_event.integrity = meta

    # Test valid
    valid_req = {
        "event": sample_canonical_event.model_dump(mode="json"),
        "expected_digest": meta.digest,
        "phase": "enriched",
    }
    resp_valid = test_client.post("/v1/verify", json=valid_req)
    assert resp_valid.status_code == 200
    assert resp_valid.json()["valid"] is True

    # Test invalid digest
    invalid_req = {
        "event": sample_canonical_event.model_dump(mode="json"),
        "expected_digest": "0" * 64,
        "phase": "enriched",
    }
    resp_invalid = test_client.post("/v1/verify", json=invalid_req)
    assert resp_invalid.status_code == 200
    assert resp_invalid.json()["valid"] is False


def test_api_rbac_forbidden_for_unauthorized_role(
    test_client: TestClient, sample_canonical_event: CanonicalEvent
) -> None:
    """Analyst key cannot call POST /v1/enrich (requires event_processing or admin)."""
    payload = {"event": sample_canonical_event.model_dump(mode="json")}
    resp = test_client.post(
        "/v1/enrich",
        json=payload,
        headers={"X-API-Key": "m4-analyst-key"},
    )
    assert resp.status_code == 403
