"""
Integration Pipeline Tests for ULPF M5 (Definition of Done Requirements 1-6).
Verifies complete flow from incoming UES event through Policy Engine, Smart Router,
and destination connectors (SIEM, Data Lake, AI Stream), including multi-routing,
failure isolation, retries, DLQ, and idempotency.
"""
import pytest
import os
import app.main as main_module
from app.main import initialize_m5_components, process_event


def setup_m5_test_environment():
    """
    Initialize complete M5 components with default test policies.
    """
    os.environ["OPENSEARCH_MOCK_MODE"] = "true"
    os.environ["DATA_LAKE_MOCK_MODE"] = "true"
    os.environ["KAFKA_MOCK_MODE"] = "true"
    os.environ["HTTP_MOCK_MODE"] = "true"
    os.environ["MAX_DELIVERY_RETRIES"] = "3"
    os.environ["INITIAL_RETRY_BACKOFF_SEC"] = "0.01"

    policy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "policies", "default.yaml"))
    initialize_m5_components(policy_file=policy_path)


@pytest.fixture(autouse=True)
def auto_setup_m5():
    setup_m5_test_environment()



async def test_dod_1_siem_indexing():
    """DOD 1: Standard UES event indexed into SIEM with idempotency."""
    event = {
        "event": {
            "id": "evt_dod_siem_01",
            "timestamp": "2026-09-13T10:00:00Z",
            "type": "authentication",
            "severity": {"value": 4}
        },
        "tenant_id": "tenant_alpha"
    }

    result = await process_event(event)

    assert result["status"] == "processed"
    assert "siem" in result["delivery_results"]
    assert result["delivery_results"]["siem"] is True

    opensearch_conn = main_module.connectors_pool["siem"]
    doc = opensearch_conn.get_mock_document("evt_dod_siem_01")
    assert doc is not None
    assert doc["event_id"] == "evt_dod_siem_01"


async def test_dod_2_datalake_writing():
    """DOD 2: UES event partitioned and written to Data Lake storage."""
    event = {
        "event": {
            "id": "evt_dod_lake_02",
            "timestamp": "2026-09-13T10:05:00Z",
            "type": "audit",
            "severity": {"value": 2}
        },
        "tenant": {"id": "tenant_alpha"}
    }

    result = await process_event(event)

    assert result["status"] == "processed"
    assert "data_lake" in result["delivery_results"]
    assert result["delivery_results"]["data_lake"] is True

    lake_conn = main_module.connectors_pool["data_lake"]
    assert "evt_dod_lake_02" in lake_conn.processed_event_ids


async def test_dod_3_ai_stream():
    """DOD 3: Telemetry event streamed to real-time AI Kafka topic."""
    # Matches alpha tenant policy (severity >= 3 for tenant_alpha -> ai_stream)
    event = {
        "event": {
            "id": "evt_dod_ai_03",
            "type": "metric_stream",
            "severity": {"value": 3}
        },
        "tenant": {"id": "tenant_alpha"}
    }

    result = await process_event(event)

    assert result["status"] == "processed"
    assert "ai_stream" in result["delivery_results"]
    assert result["delivery_results"]["ai_stream"] is True

    kafka_conn = main_module.connectors_pool["ai_stream"]
    events = kafka_conn.get_mock_events("ulpf.ai.events")
    found = any(e.get("event", {}).get("id") == "evt_dod_ai_03" for e in events)
    assert found is True


async def test_dod_4_multi_routing():
    """DOD 4: Critical security event routed concurrently to SIEM, Data Lake, and AI Stream."""
    critical_event = {
        "event": {
            "id": "evt_dod_multi_04",
            "timestamp": "2026-09-13T10:15:00Z",
            "type": "perimeter_breach",
            "severity": {"value": 5}
        },
        "security": {"is_security_event": True},
        "tenant": {"id": "tenant_enterprise"}
    }

    result = await process_event(critical_event)

    assert result["status"] == "processed"
    dests = result["delivery_results"]
    assert "siem" in dests and dests["siem"] is True
    assert "data_lake" in dests and dests["data_lake"] is True
    assert "ai_stream" in dests and dests["ai_stream"] is True


async def test_dod_5_failure_and_dlq():
    """DOD 5: Temporary connector failure retries, isolates destination, and promotes to DLQ without failing healthy sinks."""
    siem_conn = main_module.connectors_pool["siem"]

    # Temporarily simulate SIEM destination outage
    original_send = siem_conn.send

    async def broken_send(ev):
        raise ConnectionError("Simulated temporary network failure")

    siem_conn.send = broken_send

    try:
        event = {
            "event": {
                "id": "evt_dod_fail_05",
                "type": "auth",
                "severity": {"value": 4}
            }
        }

        result = await process_event(event)

        assert result["status"] == "processed"
        # SIEM should fail after retry exhaustion
        assert result["delivery_results"]["siem"] is False
        # Data Lake should remain successful (Failure Isolation!)
        assert result["delivery_results"]["data_lake"] is True

        # Verify promotion to DLQ
        dlq_records = main_module.dlq.get_records()
        matching = [r for r in dlq_records if r.event_id == "evt_dod_fail_05"]
        assert len(matching) >= 1
        assert matching[-1].destination == "siem"
    finally:
        siem_conn.send = original_send


async def test_dod_6_idempotency():
    """DOD 6: Duplicate event delivery with same event.id is idempotent."""
    event = {
        "event": {
            "id": "evt_dod_idem_06",
            "type": "system",
            "severity": {"value": 4}
        },
        "tenant_id": "tenant_alpha"
    }

    # Delivery 1
    res1 = await process_event(event)
    assert res1["status"] == "processed"

    # Delivery 2 (Exact duplicate event)
    res2 = await process_event(event)
    assert res2["status"] == "processed"

    opensearch_conn = main_module.connectors_pool["siem"]
    # OpenSearch document should be updated in place without duplicate documents
    assert "evt_dod_idem_06" in opensearch_conn.mock_storage
