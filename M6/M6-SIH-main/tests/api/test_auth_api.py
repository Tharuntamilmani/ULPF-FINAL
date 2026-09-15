"""API tests for authentication endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(app_client: AsyncClient):
    resp = await app_client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "Admin@12345"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_wrong_password(app_client: AsyncClient):
    resp = await app_client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(app_client: AsyncClient):
    resp = await app_client.post(
        "/api/v1/auth/login",
        data={"username": "nobody", "password": "anything"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(app_client: AsyncClient, auth_headers: dict):
    resp = await app_client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "admin"
    assert body["is_superuser"] is True


@pytest.mark.asyncio
async def test_get_me_unauthenticated(app_client: AsyncClient):
    resp = await app_client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token(app_client: AsyncClient):
    resp = await app_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401
