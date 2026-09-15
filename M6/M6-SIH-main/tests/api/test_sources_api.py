"""API tests for Source Registry endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

SOURCE_PAYLOAD = {
    "source_id": "api-test-src-01",
    "name": "API Test Source",
    "vendor": "Cisco",
    "product": "ASA",
    "source_type": "firewall",
    "protocol": "syslog",
    "transport": "udp",
    "port": 514,
    "zone": "dmz",
}


@pytest.mark.asyncio
async def test_create_source(app_client: AsyncClient, auth_headers: dict):
    resp = await app_client.post("/api/v1/sources", json=SOURCE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["source_id"] == "api-test-src-01"
    assert body["status"] == "active"


@pytest.mark.asyncio
async def test_create_source_duplicate(app_client: AsyncClient, auth_headers: dict):
    await app_client.post("/api/v1/sources", json=SOURCE_PAYLOAD, headers=auth_headers)
    resp = await app_client.post("/api/v1/sources", json=SOURCE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "DUPLICATE"


@pytest.mark.asyncio
async def test_list_sources(app_client: AsyncClient, auth_headers: dict):
    await app_client.post("/api/v1/sources", json=SOURCE_PAYLOAD, headers=auth_headers)
    resp = await app_client.get("/api/v1/sources", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_get_source_by_id(app_client: AsyncClient, auth_headers: dict):
    create_resp = await app_client.post(
        "/api/v1/sources", json=SOURCE_PAYLOAD, headers=auth_headers
    )
    source_id = create_resp.json()["id"]
    resp = await app_client.get(f"/api/v1/sources/{source_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["source_id"] == "api-test-src-01"


@pytest.mark.asyncio
async def test_get_source_not_found(app_client: AsyncClient, auth_headers: dict):
    resp = await app_client.get("/api/v1/sources/nonexistent-uuid", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "SOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_source(app_client: AsyncClient, auth_headers: dict):
    create_resp = await app_client.post(
        "/api/v1/sources", json=SOURCE_PAYLOAD, headers=auth_headers
    )
    sid = create_resp.json()["id"]
    resp = await app_client.put(
        f"/api/v1/sources/{sid}", json={"name": "Updated Name"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_disable_enable_source(app_client: AsyncClient, auth_headers: dict):
    create_resp = await app_client.post(
        "/api/v1/sources", json=SOURCE_PAYLOAD, headers=auth_headers
    )
    sid = create_resp.json()["id"]

    resp = await app_client.post(f"/api/v1/sources/{sid}/disable", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"

    resp = await app_client.post(f"/api/v1/sources/{sid}/enable", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


@pytest.mark.asyncio
async def test_delete_source(app_client: AsyncClient, auth_headers: dict):
    create_resp = await app_client.post(
        "/api/v1/sources", json=SOURCE_PAYLOAD, headers=auth_headers
    )
    sid = create_resp.json()["id"]
    resp = await app_client.delete(f"/api/v1/sources/{sid}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await app_client.get(f"/api/v1/sources/{sid}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_sources_unauthenticated(app_client: AsyncClient):
    resp = await app_client.get("/api/v1/sources")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_source_search_filter(app_client: AsyncClient, auth_headers: dict):
    await app_client.post("/api/v1/sources", json=SOURCE_PAYLOAD, headers=auth_headers)
    await app_client.post(
        "/api/v1/sources",
        json={**SOURCE_PAYLOAD, "source_id": "other-src", "vendor": "Palo Alto"},
        headers=auth_headers,
    )
    resp = await app_client.get("/api/v1/sources?vendor=Cisco", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["vendor"] == "Cisco" for i in items)
