"""
Tenant Security Test Matrix & Adversarial Bypass Attack Tests (Phases 22 & 23).
Verifies:
  - SUPER_ADMIN / ADMINISTRATOR platform-wide permissions
  - TENANT_ADMIN / SECURITY_ANALYST / VIEWER tenant isolation
  - 15+ Adversarial bypass attacks (spoofing query, body, headers, IDOR, suspension, etc.)
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import create_access_token, hash_password
from backend.app.models.policy import Policy
from backend.app.models.source import Source, SourceStatus
from backend.app.models.tenant import Tenant, TenantStatus
from backend.app.models.user import Role, User, UserRole


@pytest.fixture
async def tenant_setup(seeded_db: AsyncSession):
    """Setup Tenant A, Tenant B, Suspended Tenant S, and Disabled Tenant D."""
    from sqlalchemy import select

    # Tenants
    ta = Tenant(id="tenant-a-uuid", name="Tenant A", slug="tenant-a", status=TenantStatus.ACTIVE)
    tb = Tenant(id="tenant-b-uuid", name="Tenant B", slug="tenant-b", status=TenantStatus.ACTIVE)
    ts = Tenant(id="tenant-s-uuid", name="Tenant S", slug="tenant-s", status=TenantStatus.SUSPENDED)
    td = Tenant(id="tenant-d-uuid", name="Tenant D", slug="tenant-d", status=TenantStatus.DISABLED)
    seeded_db.add_all([ta, tb, ts, td])
    await seeded_db.flush()

    # Roles - reuse existing from seeded_db or create
    res = await seeded_db.execute(select(Role))
    existing_roles = {r.name: r for r in res.scalars().all()}

    def get_or_create_role(name: str, desc: str) -> Role:
        if name in existing_roles:
            return existing_roles[name]
        r = Role(name=name, description=desc)
        seeded_db.add(r)
        existing_roles[name] = r
        return r

    r_super = get_or_create_role("SUPER_ADMIN", "Super Admin")
    r_admin = get_or_create_role("ADMINISTRATOR", "Admin Alias")
    r_tadmin = get_or_create_role("TENANT_ADMIN", "Tenant Admin")
    r_analyst = get_or_create_role("SECURITY_ANALYST", "Security Analyst")
    r_viewer = get_or_create_role("VIEWER", "Viewer")
    await seeded_db.flush()

    # Users
    u_super = User(
        id="user-super-uuid",
        username="superadmin",
        email="super@test.local",
        hashed_password=hash_password("Super@123"),
        is_superuser=True,
        tenant_id=None,
    )
    u_admin_a = User(
        id="user-admin-a-uuid",
        username="admin_a",
        email="admin_a@test.local",
        hashed_password=hash_password("AdminA@123"),
        is_superuser=False,
        tenant_id=ta.id,
    )
    u_admin_b = User(
        id="user-admin-b-uuid",
        username="admin_b",
        email="admin_b@test.local",
        hashed_password=hash_password("AdminB@123"),
        is_superuser=False,
        tenant_id=tb.id,
    )
    u_analyst_a = User(
        id="user-analyst-a-uuid",
        username="analyst_a",
        email="analyst_a@test.local",
        hashed_password=hash_password("AnalystA@123"),
        is_superuser=False,
        tenant_id=ta.id,
    )
    u_viewer_a = User(
        id="user-viewer-a-uuid",
        username="viewer_a",
        email="viewer_a@test.local",
        hashed_password=hash_password("ViewerA@123"),
        is_superuser=False,
        tenant_id=ta.id,
    )
    u_suspended = User(
        id="user-suspended-uuid",
        username="suspended_user",
        email="suspended@test.local",
        hashed_password=hash_password("Suspended@123"),
        is_superuser=False,
        tenant_id=ts.id,
    )
    u_disabled = User(
        id="user-disabled-uuid",
        username="disabled_user",
        email="disabled@test.local",
        hashed_password=hash_password("Disabled@123"),
        is_superuser=False,
        tenant_id=td.id,
    )
    seeded_db.add_all(
        [u_super, u_admin_a, u_admin_b, u_analyst_a, u_viewer_a, u_suspended, u_disabled]
    )
    await seeded_db.flush()

    # Role mappings
    seeded_db.add_all(
        [
            UserRole(user_id=u_super.id, role_id=r_super.id),
            UserRole(user_id=u_admin_a.id, role_id=r_tadmin.id),
            UserRole(user_id=u_admin_b.id, role_id=r_tadmin.id),
            UserRole(user_id=u_analyst_a.id, role_id=r_analyst.id),
            UserRole(user_id=u_viewer_a.id, role_id=r_viewer.id),
            UserRole(user_id=u_suspended.id, role_id=r_tadmin.id),
            UserRole(user_id=u_disabled.id, role_id=r_tadmin.id),
        ]
    )

    # Pre-seed resources for Tenant A and Tenant B
    src_a = Source(
        source_id="src-a-1",
        tenant_id=ta.id,
        name="Source A 1",
        vendor="Cisco",
        product="ASA",
        source_type="firewall",
        protocol="syslog",
        transport="udp",
        status=SourceStatus.ACTIVE,
    )
    src_b = Source(
        source_id="src-b-1",
        tenant_id=tb.id,
        name="Source B 1",
        vendor="PaloAlto",
        product="PAN-OS",
        source_type="firewall",
        protocol="syslog",
        transport="tcp",
        status=SourceStatus.ACTIVE,
    )
    pol_a = Policy(
        policy_id="pol-a-1",
        tenant_id=ta.id,
        name="Policy A 1",
        version="1.0.0",
        priority=50,
        is_enabled=True,
        conditions=[{"field": "severity", "operator": ">=", "value": 4}],
        destinations=["kafka://alerts"],
    )
    pol_b = Policy(
        policy_id="pol-b-1",
        tenant_id=tb.id,
        name="Policy B 1",
        version="1.0.0",
        priority=50,
        is_enabled=True,
        conditions=[{"field": "severity", "operator": ">=", "value": 1}],
        destinations=["kafka://debug"],
    )
    seeded_db.add_all([src_a, src_b, pol_a, pol_b])
    await seeded_db.commit()

    return {
        "ta": ta,
        "tb": tb,
        "ts": ts,
        "td": td,
        "u_super": u_super,
        "u_admin_a": u_admin_a,
        "u_admin_b": u_admin_b,
        "u_analyst_a": u_analyst_a,
        "u_viewer_a": u_viewer_a,
        "u_suspended": u_suspended,
        "u_disabled": u_disabled,
        "src_a": src_a,
        "src_b": src_b,
        "pol_a": pol_a,
        "pol_b": pol_b,
    }


def _auth(user: User, role: str, tenant_id: str | None) -> dict[str, str]:
    token = create_access_token(
        subject=user.id,
        extra_claims={"roles": [role], "tenant_id": tenant_id, "role": role},
    )
    return {"Authorization": f"Bearer {token}"}


# ── Phase 22: Security Test Matrix ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_super_admin_cross_tenant_access(app_client: AsyncClient, tenant_setup: dict):
    env = tenant_setup
    headers = _auth(env["u_super"], "SUPER_ADMIN", None)

    # Super admin can read Tenant A sources by specifying ?tenant_id=
    resp_a = await app_client.get(f"/api/v1/sources?tenant_id={env['ta'].id}", headers=headers)
    assert resp_a.status_code == 200
    ids_a = [s["source_id"] for s in resp_a.json()["items"]]
    assert "src-a-1" in ids_a
    assert "src-b-1" not in ids_a

    # Super admin can read Tenant B sources
    resp_b = await app_client.get(f"/api/v1/sources?tenant_id={env['tb'].id}", headers=headers)
    assert resp_b.status_code == 200
    ids_b = [s["source_id"] for s in resp_b.json()["items"]]
    assert "src-b-1" in ids_b
    assert "src-a-1" not in ids_b


@pytest.mark.asyncio
async def test_tenant_admin_isolation(app_client: AsyncClient, tenant_setup: dict):
    env = tenant_setup
    headers_a = _auth(env["u_admin_a"], "TENANT_ADMIN", env["ta"].id)
    headers_b = _auth(env["u_admin_b"], "TENANT_ADMIN", env["tb"].id)

    # Tenant A admin sees ONLY Tenant A sources
    resp = await app_client.get("/api/v1/sources", headers=headers_a)
    assert resp.status_code == 200
    ids = [s["source_id"] for s in resp.json()["items"]]
    assert "src-a-1" in ids
    assert "src-b-1" not in ids

    # Tenant A admin cannot read Tenant B source by direct ID (IDOR prevention -> 404)
    resp = await app_client.get(f"/api/v1/sources/{env['src_b'].id}", headers=headers_a)
    assert resp.status_code == 404

    # Tenant A admin cannot modify Tenant B source
    resp = await app_client.put(
        f"/api/v1/sources/{env['src_b'].id}",
        json={"name": "Hacked B"},
        headers=headers_a,
    )
    assert resp.status_code == 404

    # Tenant A admin cannot delete Tenant B source
    resp = await app_client.delete(f"/api/v1/sources/{env['src_b'].id}", headers=headers_a)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_security_analyst_permissions(app_client: AsyncClient, tenant_setup: dict):
    env = tenant_setup
    headers = _auth(env["u_analyst_a"], "SECURITY_ANALYST", env["ta"].id)

    # Analyst can read Tenant A sources
    resp = await app_client.get("/api/v1/sources", headers=headers)
    assert resp.status_code == 200
    ids = [s["source_id"] for s in resp.json()["items"]]
    assert "src-a-1" in ids

    # Analyst CANNOT write Tenant A sources (403 Forbidden)
    resp = await app_client.post(
        "/api/v1/sources",
        json={
            "source_id": "src-analyst",
            "name": "Analyst Src",
            "vendor": "V",
            "product": "P",
            "source_type": "firewall",
            "protocol": "syslog",
            "transport": "udp",
        },
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_permissions(app_client: AsyncClient, tenant_setup: dict):
    env = tenant_setup
    headers = _auth(env["u_viewer_a"], "VIEWER", env["ta"].id)

    # Viewer can read Tenant A sources
    resp = await app_client.get("/api/v1/sources", headers=headers)
    assert resp.status_code == 200

    # Viewer CANNOT write (403 Forbidden)
    resp = await app_client.post(
        "/api/v1/sources",
        json={
            "source_id": "src-viewer",
            "name": "Viewer Src",
            "vendor": "V",
            "product": "P",
            "source_type": "firewall",
            "protocol": "syslog",
            "transport": "udp",
        },
        headers=headers,
    )
    assert resp.status_code == 403


# ── Phase 23: Adversarial Tenant Bypass Attacks ────────────────────────────────


@pytest.mark.asyncio
async def test_attack_1_query_param_spoofing(app_client: AsyncClient, tenant_setup: dict):
    """Attack 1: Tenant A attempts ?tenant_id=tenant-b-uuid -> must 403 Forbidden."""
    env = tenant_setup
    headers = _auth(env["u_admin_a"], "TENANT_ADMIN", env["ta"].id)

    resp = await app_client.get(f"/api/v1/sources?tenant_id={env['tb'].id}", headers=headers)
    assert resp.status_code == 403
    assert "Cross-tenant access forbidden" in resp.text


@pytest.mark.asyncio
async def test_attack_2_json_body_tenant_spoofing(app_client: AsyncClient, tenant_setup: dict):
    """Attack 2: Tenant A attempts to set tenant_id=TenantB in body -> must be overridden to Tenant A."""
    env = tenant_setup
    headers = _auth(env["u_admin_a"], "TENANT_ADMIN", env["ta"].id)

    resp = await app_client.post(
        "/api/v1/sources",
        json={
            "source_id": "attack-src-2",
            "tenant_id": env["tb"].id,  # Malicious attempt
            "name": "Spoofed Source",
            "vendor": "V",
            "product": "P",
            "source_type": "firewall",
            "protocol": "syslog",
            "transport": "udp",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    # Verify server assigned Tenant A, not Tenant B
    assert resp.json()["tenant_id"] == env["ta"].id


@pytest.mark.asyncio
async def test_attack_3_header_spoofing(app_client: AsyncClient, tenant_setup: dict):
    """Attack 3: X-Tenant-ID header spoofing must be ignored."""
    env = tenant_setup
    headers = _auth(env["u_admin_a"], "TENANT_ADMIN", env["ta"].id)
    headers["X-Tenant-ID"] = env["tb"].id

    resp = await app_client.get("/api/v1/sources", headers=headers)
    assert resp.status_code == 200
    ids = [s["source_id"] for s in resp.json()["items"]]
    assert "src-b-1" not in ids


@pytest.mark.asyncio
async def test_attack_4_direct_policy_idor(app_client: AsyncClient, tenant_setup: dict):
    """Attack 4: Direct IDOR on Policy of Tenant B -> 404 Not Found."""
    env = tenant_setup
    headers = _auth(env["u_admin_a"], "TENANT_ADMIN", env["ta"].id)

    resp = await app_client.get(f"/api/v1/policies/{env['pol_b'].id}", headers=headers)
    assert resp.status_code == 404

    resp = await app_client.put(
        f"/api/v1/policies/{env['pol_b'].id}",
        json={"name": "Hacked Policy"},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_attack_5_user_management_isolation(app_client: AsyncClient, tenant_setup: dict):
    """Attack 5: Tenant A admin cannot create or modify users in Tenant B."""
    env = tenant_setup
    headers = _auth(env["u_admin_a"], "TENANT_ADMIN", env["ta"].id)

    # Cannot create user in Tenant B
    resp = await app_client.post(
        "/api/v1/auth/users",
        json={
            "username": "rogue_user_b",
            "email": "rogue_b@example.com",
            "password": "Password123!",
            "role": "VIEWER",
            "tenant_id": env["tb"].id,
        },
        headers=headers,
    )
    assert resp.status_code == 403

    # Cannot view Tenant B user
    resp = await app_client.get(f"/api/v1/auth/users/{env['u_admin_b'].id}", headers=headers)
    assert resp.status_code == 404

    # Cannot reassign user to Tenant B
    resp = await app_client.put(
        f"/api/v1/auth/users/{env['u_analyst_a'].id}",
        json={"tenant_id": env["tb"].id},
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_attack_6_audit_log_isolation(app_client: AsyncClient, tenant_setup: dict):
    """Attack 6: Tenant user only views own tenant audit trail."""
    env = tenant_setup
    headers = _auth(env["u_admin_a"], "TENANT_ADMIN", env["ta"].id)

    # Attempt to query Tenant B's audit events
    resp = await app_client.get(f"/api/v1/audit?tenant_id={env['tb'].id}", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_attack_7_suspended_tenant_rejected(app_client: AsyncClient, tenant_setup: dict):
    """Attack 7: User with suspended tenant is rejected even with valid JWT signature."""
    env = tenant_setup
    headers = _auth(env["u_suspended"], "TENANT_ADMIN", env["ts"].id)

    resp = await app_client.get("/api/v1/sources", headers=headers)
    assert resp.status_code == 403
    assert "suspended or disabled" in resp.text.lower()


@pytest.mark.asyncio
async def test_attack_8_disabled_tenant_rejected(app_client: AsyncClient, tenant_setup: dict):
    """Attack 8: User with disabled tenant is rejected even with valid JWT signature."""
    env = tenant_setup
    headers = _auth(env["u_disabled"], "TENANT_ADMIN", env["td"].id)

    resp = await app_client.get("/api/v1/sources", headers=headers)
    assert resp.status_code == 403
    assert "suspended or disabled" in resp.text.lower()


@pytest.mark.asyncio
async def test_attack_9_parser_extension_isolation(app_client: AsyncClient, tenant_setup: dict):
    """Attack 9: Parser extensions are isolated per tenant."""
    env = tenant_setup
    headers_b = _auth(env["u_admin_b"], "TENANT_ADMIN", env["tb"].id)
    headers_a = _auth(env["u_admin_a"], "TENANT_ADMIN", env["ta"].id)

    # Tenant B creates extension
    resp = await app_client.post(
        "/api/v1/parsers",
        json={
            "parser_id": "custom-ext",
            "name": "Custom Extension B",
            "vendor": "V",
            "product": "P",
            "format": "syslog",
            "version": "1.0.0",
        },
        headers=headers_b,
    )
    assert resp.status_code == 201
    p_b_id = resp.json()["id"]

    # Tenant A cannot see Tenant B's extension
    resp = await app_client.get(f"/api/v1/parsers/{p_b_id}", headers=headers_a)
    assert resp.status_code == 404
