"""
Comprehensive Test Suite covering all 23 Required Audit Scenarios (TEST 01 to TEST 23)
from Section 29 of the ULPF M5 Specification.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
import app.main as main_module
from app.main import app, initialize_m5_components, process_event
from app.router.router import SmartRouter
from app.router.rules import PolicyRule
from app.delivery.ack import AckTracker
from app.delivery.dlq import DeadLetterQueue
from app.delivery.retry import RetryEngine
from app.connectors.base import DestinationConnector
from app.api.auth import TenantContext
from app.api.events import get_event_by_id
from app.api.search import search_events, EventSearchQuery


@pytest.fixture(autouse=True)
def init_test_env():
    policy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "policies", "default.yaml"))
    initialize_m5_components(policy_file=policy_path)


# TEST 01: Normal UES event -> SIEM
@pytest.mark.asyncio
async def test_scenario_01_normal_event_to_siem():
    event = {
        "event": {
            "id": "evt_t01_siem",
            "type": "auth",
            "severity": {"value": 4}
        },
        "tenant_id": "tenant_alpha"
    }
    res = await process_event(event)
    assert res["status"] == "processed"
    assert "siem" in res["delivery_results"]
    assert res["delivery_results"]["siem"] is True
    doc = main_module.connectors_pool["siem"].get_mock_document("evt_t01_siem")
    assert doc is not None
    assert doc["event_id"] == "evt_t01_siem"


# TEST 02: Normal UES event -> Data Lake
@pytest.mark.asyncio
async def test_scenario_02_normal_event_to_datalake():
    event = {
        "event": {
            "id": "evt_t02_lake",
            "type": "audit",
            "severity": {"value": 2}
        },
        "tenant": {"id": "tenant_alpha"}
    }
    res = await process_event(event)
    assert res["status"] == "processed"
    assert "data_lake" in res["delivery_results"]
    assert res["delivery_results"]["data_lake"] is True
    assert "evt_t02_lake" in main_module.connectors_pool["data_lake"].processed_event_ids


# TEST 03: Normal UES event -> AI stream
@pytest.mark.asyncio
async def test_scenario_03_normal_event_to_ai_stream():
    event = {
        "event": {
            "id": "evt_t03_ai",
            "type": "telemetry",
            "severity": {"value": 3}
        },
        "tenant": {"id": "tenant_alpha"}
    }
    res = await process_event(event)
    assert res["status"] == "processed"
    assert "ai_stream" in res["delivery_results"]
    assert res["delivery_results"]["ai_stream"] is True
    ai_events = main_module.connectors_pool["ai_stream"].get_mock_events("ulpf.ai.events")
    assert any(e.get("event", {}).get("id") == "evt_t03_ai" for e in ai_events)


# TEST 04: Critical security event -> all required destinations
@pytest.mark.asyncio
async def test_scenario_04_critical_security_event_all_destinations():
    critical_event = {
        "event": {
            "id": "evt_t04_crit",
            "type": "network_intrusion",
            "severity": {"value": 5}
        },
        "security": {"is_security_event": True},
        "tenant": {"id": "tenant_enterprise"}
    }
    res = await process_event(critical_event)
    assert res["status"] == "processed"
    assert res["delivery_results"]["siem"] is True
    assert res["delivery_results"]["data_lake"] is True
    assert res["delivery_results"]["ai_stream"] is True


# TEST 05: Two policies match one event
@pytest.mark.asyncio
async def test_scenario_05_two_policies_match_one_event():
    router = SmartRouter()
    r1 = PolicyRule(id="p1", priority=10, when={"field": "event.type", "operator": "==", "value": "auth"}, destinations=["siem"])
    r2 = PolicyRule(id="p2", priority=20, when={"field": "event.severity.value", "operator": ">=", "value": 4}, destinations=["data_lake"])
    router.set_rules([r1, r2])

    event = {"event": {"id": "evt_t05", "type": "auth", "severity": {"value": 4}}}
    dests, decision = router.route(event)
    assert len(decision.matched_policies) == 2
    assert "p1" in decision.matched_policies
    assert "p2" in decision.matched_policies
    assert "siem" in dests and "data_lake" in dests


# TEST 06: No policy matches
@pytest.mark.asyncio
async def test_scenario_06_no_policy_matches():
    router = SmartRouter()
    r = PolicyRule(id="strict-rule", when={"field": "event.type", "operator": "==", "value": "non_existent"}, destinations=["siem"])
    router.set_rules([r])

    event = {"event": {"id": "evt_t06", "type": "heartbeat"}}
    dests, decision = router.route(event)
    assert len(dests) == 0
    assert len(decision.matched_policies) == 0


# TEST 07: Tenant-specific routing
@pytest.mark.asyncio
async def test_scenario_07_tenant_specific_routing():
    router = SmartRouter()
    r_alpha = PolicyRule(id="alpha-rule", tenant_id="tenant_alpha", destinations=["ai_stream"])
    r_beta = PolicyRule(id="beta-rule", tenant_id="tenant_beta", destinations=["siem"])
    router.set_rules([r_alpha, r_beta])

    ev_alpha = {"event": {"id": "evt_t07_a"}, "tenant": {"id": "tenant_alpha"}}
    dests_a, dec_a = router.route(ev_alpha)
    assert dests_a == ["ai_stream"]

    ev_beta = {"event": {"id": "evt_t07_b"}, "tenant": {"id": "tenant_beta"}}
    dests_b, dec_b = router.route(ev_beta)
    assert dests_b == ["siem"]


# TEST 08: Tenant A cannot access Tenant B
@pytest.mark.asyncio
async def test_scenario_08_tenant_isolation_denied():
    # Index event for tenant_a
    ev_a = {"event": {"id": "evt_t08_priv", "type": "auth", "severity": {"value": 4}}, "tenant_id": "tenant_a"}
    await process_event(ev_a)

    tenant_b_ctx = TenantContext(tenant_id="tenant_b", is_admin=False)
    with pytest.raises(HTTPException) as exc:
        await get_event_by_id("evt_t08_priv", context=tenant_b_ctx)
    assert exc.value.status_code == 403


# Helper Mock Connector for destination outage simulation
class TemporarilyFailingConnector(DestinationConnector):
    def __init__(self, name: str, fail_until_attempt: int = 1):
        self._name = name
        self.attempts = 0
        self.fail_until = fail_until_attempt

    def name(self) -> str: return self._name

    async def send(self, event):
        self.attempts += 1
        if self.attempts <= self.fail_until:
            raise ConnectionError(f"Simulated outage on {self._name}")

    async def health(self) -> bool: return self.attempts > self.fail_until


# TEST 09: OpenSearch temporarily unavailable
@pytest.mark.asyncio
async def test_scenario_09_opensearch_temporarily_unavailable():
    tracker = AckTracker()
    dlq = DeadLetterQueue()
    engine = RetryEngine(max_retries=3, initial_backoff_sec=0.01, ack_tracker=tracker, dlq=dlq)
    flaky = TemporarilyFailingConnector("siem", fail_until_attempt=1)
    ev = {"event": {"id": "evt_t09"}}
    ok = await engine.deliver_to_connector(flaky, ev)
    assert ok is True
    assert flaky.attempts == 2


# TEST 10: Data Lake temporarily unavailable
@pytest.mark.asyncio
async def test_scenario_10_datalake_temporarily_unavailable():
    tracker = AckTracker()
    dlq = DeadLetterQueue()
    engine = RetryEngine(max_retries=3, initial_backoff_sec=0.01, ack_tracker=tracker, dlq=dlq)
    flaky = TemporarilyFailingConnector("data_lake", fail_until_attempt=2)
    ev = {"event": {"id": "evt_t10"}}
    ok = await engine.deliver_to_connector(flaky, ev)
    assert ok is True
    assert flaky.attempts == 3


# TEST 11: AI stream temporarily unavailable
@pytest.mark.asyncio
async def test_scenario_11_ai_stream_temporarily_unavailable():
    tracker = AckTracker()
    dlq = DeadLetterQueue()
    engine = RetryEngine(max_retries=3, initial_backoff_sec=0.01, ack_tracker=tracker, dlq=dlq)
    flaky = TemporarilyFailingConnector("ai_stream", fail_until_attempt=1)
    ev = {"event": {"id": "evt_t11"}}
    ok = await engine.deliver_to_connector(flaky, ev)
    assert ok is True
    assert flaky.attempts == 2


# TEST 12: Retry succeeds
@pytest.mark.asyncio
async def test_scenario_12_retry_succeeds():
    tracker = AckTracker()
    engine = RetryEngine(max_retries=3, initial_backoff_sec=0.01, ack_tracker=tracker)
    flaky = TemporarilyFailingConnector("siem", fail_until_attempt=1)
    ev = {"event": {"id": "evt_t12"}}
    ok = await engine.deliver_to_connector(flaky, ev)
    assert ok is True
    st = tracker.get_status("evt_t12", "siem")
    assert st.attempts == 2
    assert st.status.value == "ACKNOWLEDGED"


# TEST 13: Retry exhausted -> DLQ
@pytest.mark.asyncio
async def test_scenario_13_retry_exhausted_promotes_dlq():
    tracker = AckTracker()
    dlq = DeadLetterQueue()
    engine = RetryEngine(max_retries=2, initial_backoff_sec=0.01, ack_tracker=tracker, dlq=dlq)
    dead = TemporarilyFailingConnector("siem", fail_until_attempt=5)
    ev = {"event": {"id": "evt_t13"}}
    ok = await engine.deliver_to_connector(dead, ev)
    assert ok is False
    assert dead.attempts == 2
    assert len(dlq.get_records()) >= 1
    assert dlq.get_records()[-1].event_id == "evt_t13"


# TEST 14: Same event delivered twice
@pytest.mark.asyncio
async def test_scenario_14_same_event_delivered_twice_idempotency():
    ev = {"event": {"id": "evt_t14_idem", "type": "auth", "severity": {"value": 4}}, "tenant_id": "tenant_alpha"}
    res1 = await process_event(ev)
    res2 = await process_event(ev)
    assert res1["status"] == "processed"
    assert res2["status"] == "processed"
    os_conn = main_module.connectors_pool["siem"]
    assert "evt_t14_idem" in os_conn.mock_storage


# TEST 15: Malformed UES input
@pytest.mark.asyncio
async def test_scenario_15_malformed_ues_input():
    # Missing event.id
    malformed_event = {"something_else": "invalid"}
    with pytest.raises(HTTPException) as exc:
        await process_event(malformed_event)
    assert exc.value.status_code == 422


# TEST 16: Invalid policy
@pytest.mark.asyncio
async def test_scenario_16_invalid_policy():
    from app.policy.loader import PolicyLoader
    # PolicyLoader handles malformed rule dictionaries safely without crashing
    raw_invalid_data = [{"id": "bad_rule", "priority": "not_an_int_invalid"}]
    rules = PolicyLoader.load_from_dict(raw_invalid_data)
    # Bad rule safely skipped
    assert len(rules) == 0


# TEST 17: Destination authentication failure
@pytest.mark.asyncio
async def test_scenario_17_destination_authentication_failure():
    from app.connectors.opensearch import OpenSearchConnector
    connector = OpenSearchConnector(connector_name="siem_auth_test", mock_mode=False)

    class Mock401Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def put(self, *args, **kwargs):
            class MockRes:
                status_code = 401
                text = "Unauthorized"
            return MockRes()

    import httpx
    orig_client = httpx.AsyncClient
    httpx.AsyncClient = lambda *args, **kwargs: Mock401Client()
    try:
        with pytest.raises(PermissionError) as exc:
            await connector.send({"event": {"id": "evt_auth_fail"}})
        assert "authentication failed" in str(exc.value).lower()
    finally:
        httpx.AsyncClient = orig_client


# TEST 18: Service dependency unavailable
@pytest.mark.asyncio
async def test_scenario_18_service_dependency_unavailable():
    client = TestClient(app)
    main_module.connectors_pool["siem"].is_healthy = False
    try:
        res = client.get("/ready")
        assert res.status_code == 503
    finally:
        main_module.connectors_pool["siem"].is_healthy = True


# TEST 19: API search
@pytest.mark.asyncio
async def test_scenario_19_api_search():
    ev = {"event": {"id": "evt_t19", "type": "auth", "severity": {"value": 4}}, "tenant_id": "tenant_alpha"}
    await process_event(ev)
    q = EventSearchQuery(event_type="auth", min_severity=3)
    res = await search_events(q, context=TenantContext(tenant_id="tenant_alpha", is_admin=False))
    assert res["count"] >= 1
    assert any(e.get("event", {}).get("id") == "evt_t19" for e in res["events"])


# TEST 20: API get-by-event-id
@pytest.mark.asyncio
async def test_scenario_20_api_get_by_event_id():
    ev = {"event": {"id": "evt_t20", "type": "auth", "severity": {"value": 4}}, "tenant_id": "tenant_alpha"}
    await process_event(ev)
    res = await get_event_by_id("evt_t20", context=TenantContext(tenant_id="tenant_alpha", is_admin=False))
    assert res["status"] == "found"
    assert res["event_id"] == "evt_t20"


# TEST 21: Health endpoint
def test_scenario_21_health_endpoint():
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.json()["ues_version"] == "1.0.0"


# TEST 22: Readiness endpoint
def test_scenario_22_readiness_endpoint():
    client = TestClient(app)
    res = client.get("/ready")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"


# TEST 23: Metrics endpoint
def test_scenario_23_metrics_endpoint():
    client = TestClient(app)
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "ulpf_routing_events_total" in res.text
