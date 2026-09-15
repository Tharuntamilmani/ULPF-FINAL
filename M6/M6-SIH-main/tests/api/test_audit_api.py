"""API tests for audit trail — verifies every mutation creates an audit entry."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_source_create_produces_audit_entry(app_client: AsyncClient, auth_headers: dict):
    await app_client.post(
        "/api/v1/sources",
        json={
            "source_id": "audit-src",
            "name": "Audit Test",
            "vendor": "Cisco",
            "product": "ASA",
            "source_type": "firewall",
            "protocol": "syslog",
            "transport": "udp",
        },
        headers=auth_headers,
    )
    resp = await app_client.get("/api/v1/audit?resource_type=source", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    actions = [e["action"] for e in items]
    assert "SOURCE_CREATED" in actions


@pytest.mark.asyncio
async def test_parser_lifecycle_produces_audit_entries(app_client: AsyncClient, auth_headers: dict):
    # Register + submit
    create_resp = await app_client.post(
        "/api/v1/parsers",
        json={
            "parser_id": "audit-parser",
            "name": "Audit Parser",
            "vendor": "V",
            "product": "P",
            "format": "syslog",
            "version": "1.0.0",
        },
        headers=auth_headers,
    )
    pid = create_resp.json()["id"]
    await app_client.post(f"/api/v1/parsers/{pid}/submit", json={}, headers=auth_headers)

    resp = await app_client.get("/api/v1/audit?resource_type=parser", headers=auth_headers)
    assert resp.status_code == 200
    actions = [e["action"] for e in resp.json()["items"]]
    assert "PARSER_REGISTERED" in actions
    assert "PARSER_SUBMITTED" in actions


@pytest.mark.asyncio
async def test_audit_list_pagination(app_client: AsyncClient, auth_headers: dict):
    resp = await app_client.get("/api/v1/audit?page=1&page_size=5", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["page"] == 1
    assert body["page_size"] == 5


@pytest.mark.asyncio
async def test_audit_requires_auth(app_client: AsyncClient):
    resp = await app_client.get("/api/v1/audit")
    assert resp.status_code == 401
