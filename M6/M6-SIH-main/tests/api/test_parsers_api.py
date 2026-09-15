"""API tests for Parser Registry endpoints including lifecycle."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

PARSER_PAYLOAD = {
    "parser_id": "api-test-parser",
    "name": "API Test Parser",
    "vendor": "Cisco",
    "product": "ASA",
    "format": "syslog",
    "version": "1.0.0",
}


@pytest.mark.asyncio
async def test_register_parser(app_client: AsyncClient, auth_headers: dict):
    resp = await app_client.post("/api/v1/parsers", json=PARSER_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["parser_id"] == "api-test-parser"
    assert body["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_parser_lifecycle_full(app_client: AsyncClient, auth_headers: dict):
    # Register
    resp = await app_client.post("/api/v1/parsers", json=PARSER_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    pid = resp.json()["id"]

    # Submit
    resp = await app_client.post(f"/api/v1/parsers/{pid}/submit", json={}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "PENDING_APPROVAL"

    # Approve
    resp = await app_client.post(
        f"/api/v1/parsers/{pid}/approve", json={"reason": "Looks good"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"

    # Activate
    resp = await app_client.post(f"/api/v1/parsers/{pid}/activate", json={}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"

    # Rollback
    resp = await app_client.post(
        f"/api/v1/parsers/{pid}/rollback", json={"reason": "Emergency"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ROLLED_BACK"


@pytest.mark.asyncio
async def test_invalid_lifecycle_transition(app_client: AsyncClient, auth_headers: dict):
    resp = await app_client.post("/api/v1/parsers", json=PARSER_PAYLOAD, headers=auth_headers)
    pid = resp.json()["id"]

    # Try to activate from DRAFT — must fail
    resp = await app_client.post(f"/api/v1/parsers/{pid}/activate", json={}, headers=auth_headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


@pytest.mark.asyncio
async def test_get_parser_history(app_client: AsyncClient, auth_headers: dict):
    resp = await app_client.post("/api/v1/parsers", json=PARSER_PAYLOAD, headers=auth_headers)
    pid = resp.json()["id"]
    await app_client.post(f"/api/v1/parsers/{pid}/submit", json={}, headers=auth_headers)

    resp = await app_client.get(f"/api/v1/parsers/{pid}/history", headers=auth_headers)
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 2  # initial + submit


@pytest.mark.asyncio
async def test_parser_not_found(app_client: AsyncClient, auth_headers: dict):
    resp = await app_client.get("/api/v1/parsers/nonexistent", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "PARSER_NOT_FOUND"
