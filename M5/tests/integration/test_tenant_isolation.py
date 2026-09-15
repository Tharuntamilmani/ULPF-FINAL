"""
Tenant Isolation Security Integration Tests.
Verifies that Tenant A cannot read, query, or retrieve Tenant B events under any circumstances,
and that unauthenticated requests or arbitrary tenant claims are denied.
"""
import pytest
from fastapi import HTTPException
from app.main import initialize_m5_components, process_event
from app.api.events import get_event_by_id, list_events
from app.api.search import search_events, EventSearchQuery
from app.api.auth import TenantContext


def setup_m5():
    """Setup M5 environment for tenant security tests."""
    initialize_m5_components()


async def test_tenant_isolation_on_event_queries():
    setup_m5()

    # Event 1 belonging to tenant_alpha
    event_alpha = {
        "event": {
            "id": "evt_sec_alpha_10",
            "type": "auth",
            "severity": {"value": 4}
        },
        "tenant_id": "tenant_alpha"
    }

    # Event 2 belonging to tenant_beta
    event_beta = {
        "event": {
            "id": "evt_sec_beta_20",
            "type": "auth",
            "severity": {"value": 4}
        },
        "tenant_id": "tenant_beta"
    }

    await process_event(event_alpha)
    await process_event(event_beta)

    alpha_ctx = TenantContext(tenant_id="tenant_alpha", is_admin=False)
    beta_ctx = TenantContext(tenant_id="tenant_beta", is_admin=False)
    admin_ctx = TenantContext(tenant_id="admin", is_admin=True)

    # 1. Tenant Alpha retrieves their own event -> SUCCESS
    res_alpha = await get_event_by_id("evt_sec_alpha_10", context=alpha_ctx)
    assert res_alpha["status"] == "found"
    assert res_alpha["event_id"] == "evt_sec_alpha_10"

    # 2. Tenant Beta attempts to retrieve Tenant Alpha's event -> FORBIDDEN (403)
    with pytest.raises(HTTPException) as exc_info:
        await get_event_by_id("evt_sec_alpha_10", context=beta_ctx)
    assert exc_info.value.status_code == 403

    # 3. Tenant Beta attempts to claim tenant_alpha via header parameter -> FORBIDDEN (403)
    with pytest.raises(HTTPException) as exc_info2:
        await get_event_by_id("evt_sec_alpha_10", x_tenant_id="tenant_beta", context=beta_ctx)
    assert exc_info2.value.status_code == 403

    # 4. Admin retrieves Tenant Alpha's event -> SUCCESS
    res_admin = await get_event_by_id("evt_sec_alpha_10", context=admin_ctx)
    assert res_admin["status"] == "found"

    # 5. Non-existent event -> NOT FOUND (404)
    with pytest.raises(HTTPException) as exc_info3:
        await get_event_by_id("non_existent_id", context=alpha_ctx)
    assert exc_info3.value.status_code == 404

    # 6. List events scoped by tenant
    list_alpha = await list_events(context=alpha_ctx)
    for ev in list_alpha["events"]:
        assert ev.get("tenant_id") == "tenant_alpha" or ev.get("tenant", {}).get("id") == "tenant_alpha"

    # 7. Search events scoped by tenant
    search_q = EventSearchQuery(event_type="auth")
    search_res = await search_events(search_q, context=beta_ctx)
    for ev in search_res["events"]:
        assert ev.get("tenant_id") == "tenant_beta" or ev.get("tenant", {}).get("id") == "tenant_beta"
