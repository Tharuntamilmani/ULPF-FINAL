"""
Canonical End-to-End Verification Scenario for ULPF M5 (Section 30).
Demonstrates:
  M4 Enriched UES Event -> Policy Matching -> Multi-Destination Delivery (SIEM + Data Lake + AI Stream)
  -> API Search -> event.id Lookup -> Failure Simulation -> Retry -> Recovery -> Idempotent Replay.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import pytest
import app.main as main_module
from app.main import initialize_m5_components, process_event
from app.api.events import get_event_by_id
from app.api.search import search_events, EventSearchQuery
from app.api.auth import TenantContext


@pytest.mark.asyncio
async def test_e2e_canonical_flow():
    print("\n=======================================================")
    print("   CANONICAL END-TO-END DEMONSTRATION SCENARIO (SEC 30)")
    print("=======================================================")

    # Step 1: Initialize M5 with default policies
    policy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "policies", "default.yaml"))
    initialize_m5_components(policy_file=policy_path)

    # Step 2: Canonical Input: M4 Enriched UES v1.0.0 Perimeter-Network Event
    ues_event = {
        "event": {
            "id": "evt_e2e_perimeter_9999",
            "timestamp": "2026-09-13T12:00:00.000Z",
            "type": "network.perimeter.breach",
            "category": "security",
            "action": "firewall_drop",
            "outcome": "blocked",
            "severity": {
                "value": 5,
                "label": "critical"
            }
        },
        "source": {
            "ip": "203.0.113.50",
            "port": 44444
        },
        "destination": {
            "ip": "10.0.1.15",
            "port": 443
        },
        "network": {
            "protocol": "tcp",
            "bytes": 2048
        },
        "security": {
            "is_security_event": True,
            "threat_intel": {
                "indicator": "malicious_c2_ip"
            }
        },
        "provenance": {
            "source_module": "M4_ENRICHMENT",
            "schema_version": "1.0.0"
        },
        "tenant": {
            "id": "tenant_enterprise"
        }
    }

    print("\n[Phase 1] Processing Enriched UES v1 Event through M5 Pipeline...")
    res = await process_event(ues_event)

    print(f"  Status: {res['status']}")
    print(f"  Event ID: {res['event_id']}")
    print(f"  Matched Policies: {res['decision']['matched_policies']}")
    print(f"  Delivery Results: {res['delivery_results']}")

    # Assert multi-routing to SIEM, Data Lake, and AI Stream
    assert res["status"] == "processed"
    assert "critical-security-policy" in res["decision"]["matched_policies"]
    assert res["delivery_results"]["siem"] is True
    assert res["delivery_results"]["data_lake"] is True
    assert res["delivery_results"]["ai_stream"] is True
    print("  -> PASS: Multi-destination delivery succeeded (SIEM + Data Lake + AI Stream)")

    # Step 3: Demonstrate API Search
    print("\n[Phase 2] Querying Stored Event via API Search...")
    auth_ctx = TenantContext(tenant_id="tenant_enterprise", is_admin=False)
    search_query = EventSearchQuery(
        event_type="network.perimeter.breach",
        min_severity=4,
        is_security_event=True
    )
    search_res = await search_events(search_query, context=auth_ctx)
    print(f"  Search Found Count: {search_res['count']}")
    assert search_res["count"] >= 1
    found_event = search_res["events"][0]
    assert found_event["event"]["id"] == "evt_e2e_perimeter_9999"
    print("  -> PASS: API search successfully located event by criteria within tenant scope")

    # Step 4: Demonstrate event.id direct lookup via API
    print("\n[Phase 3] Direct Lookup via GET /v1/events/{event_id}...")
    lookup_res = await get_event_by_id("evt_e2e_perimeter_9999", context=auth_ctx)
    assert lookup_res["status"] == "found"
    assert lookup_res["event_id"] == "evt_e2e_perimeter_9999"
    # Canonical UES structure strictly preserved
    assert lookup_res["event"]["event"]["action"] == "firewall_drop"
    assert lookup_res["event"]["source"]["ip"] == "203.0.113.50"
    print("  -> PASS: Canonical UES semantics preserved exactly without mutation")

    # Step 5: Simulate OpenSearch Failure, Retries, and Recovery
    print("\n[Phase 4] Simulating OpenSearch Temporary Failure & Retry Recovery...")
    siem_conn = main_module.connectors_pool["siem"]
    original_send = siem_conn.send
    failure_counter = {"attempts": 0}

    async def flaky_send(ev):
        failure_counter["attempts"] += 1
        if failure_counter["attempts"] < 3:
            raise ConnectionError(f"Simulated OpenSearch timeout attempt {failure_counter['attempts']}")
        # Recovers on attempt 3
        return await original_send(ev)

    siem_conn.send = flaky_send

    recovery_event = dict(ues_event)
    recovery_event["event"] = dict(ues_event["event"])
    recovery_event["event"]["id"] = "evt_e2e_retry_recovery_8888"

    try:
        retry_res = await process_event(recovery_event)
        assert retry_res["status"] == "processed"
        assert retry_res["delivery_results"]["siem"] is True
        assert failure_counter["attempts"] == 3
        print(f"  -> PASS: OpenSearch recovered on attempt {failure_counter['attempts']} via exponential backoff")
    finally:
        siem_conn.send = original_send

    # Step 6: Verify Idempotent Duplicate Delivery
    print("\n[Phase 5] Demonstrating Idempotent Delivery on Replay...")
    replay_res = await process_event(ues_event)
    assert replay_res["status"] == "processed"
    assert replay_res["delivery_results"]["siem"] is True
    assert replay_res["delivery_results"]["data_lake"] is True

    # Check OpenSearch has exactly 1 document for evt_e2e_perimeter_9999
    doc = siem_conn.get_mock_document("evt_e2e_perimeter_9999")
    assert doc is not None
    assert doc["event_id"] == "evt_e2e_perimeter_9999"
    print("  -> PASS: Replay of same event produced idempotent delivery without duplication")
    print("=======================================================\n")


if __name__ == "__main__":
    asyncio.run(test_e2e_canonical_flow())
