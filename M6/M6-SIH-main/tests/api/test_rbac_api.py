"""API tests for RBAC enforcement."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import hash_password
from backend.app.models.user import Role, User, UserRole


async def _create_user(db: AsyncSession, username: str, role_name: str) -> str:
    """Helper: create a user with a specific role and return JWT token string."""
    from sqlalchemy import select

    role = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
    if not role:
        role = Role(name=role_name, description=role_name)
        db.add(role)
        await db.flush()

    user = User(
        username=username,
        email=f"{username}@test.local",
        hashed_password=hash_password("Test@12345"),
        is_superuser=False,
        tenant_id="default-tenant-uuid",
    )
    db.add(user)
    await db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    await db.commit()
    return username


@pytest.mark.asyncio
async def test_viewer_cannot_create_source(app_client: AsyncClient, seeded_db: AsyncSession):
    await _create_user(seeded_db, "viewer-user", "VIEWER")
    resp = await app_client.post(
        "/api/v1/auth/login", data={"username": "viewer-user", "password": "Test@12345"}
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await app_client.post(
        "/api/v1/sources",
        json={
            "source_id": "x",
            "name": "x",
            "vendor": "x",
            "product": "x",
            "source_type": "x",
            "protocol": "x",
            "transport": "x",
        },
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_can_list_sources(app_client: AsyncClient, seeded_db: AsyncSession):
    await _create_user(seeded_db, "viewer-list", "VIEWER")
    resp = await app_client.post(
        "/api/v1/auth/login", data={"username": "viewer-list", "password": "Test@12345"}
    )
    token = resp.json()["access_token"]
    resp = await app_client.get("/api/v1/sources", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_parser_dev_cannot_approve(
    app_client: AsyncClient, seeded_db: AsyncSession, auth_headers: dict
):
    # First register a parser as admin
    create_resp = await app_client.post(
        "/api/v1/parsers",
        json={
            "parser_id": "rbac-test-parser",
            "name": "RBAC Parser",
            "vendor": "V",
            "product": "P",
            "format": "syslog",
            "version": "1.0.0",
        },
        headers=auth_headers,
    )
    pid = create_resp.json()["id"]
    await app_client.post(f"/api/v1/parsers/{pid}/submit", json={}, headers=auth_headers)

    # Parser developer tries to approve — must be rejected
    await _create_user(seeded_db, "parser-dev-user", "PARSER_DEVELOPER")
    resp = await app_client.post(
        "/api/v1/auth/login", data={"username": "parser-dev-user", "password": "Test@12345"}
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await app_client.post(f"/api/v1/parsers/{pid}/approve", json={}, headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_has_full_access(app_client: AsyncClient, auth_headers: dict):
    resp = await app_client.get("/api/v1/sources", headers=auth_headers)
    assert resp.status_code == 200
    resp = await app_client.get("/api/v1/parsers", headers=auth_headers)
    assert resp.status_code == 200
    resp = await app_client.get("/api/v1/policies", headers=auth_headers)
    assert resp.status_code == 200
    resp = await app_client.get("/api/v1/audit", headers=auth_headers)
    assert resp.status_code == 200
