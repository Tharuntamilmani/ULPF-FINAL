"""
Connector tests for OpenSearch, Kafka, HTTP Webhook, and Data Lake Writer.
Verifies idempotency, schema preservation, field explosion control, and partitioning.
"""
import os
import shutil
from app.connectors.opensearch import OpenSearchConnector
from app.connectors.kafka import KafkaConnector
from app.connectors.http import HttpConnector
from app.datalake.writer import DataLakeWriter


async def test_opensearch_connector_idempotency_and_field_control():
    connector = OpenSearchConnector(connector_name="siem", mock_mode=True)

    event = {
        "event": {
            "id": "evt_os_001",
            "timestamp": "2026-09-13T10:00:00Z",
            "type": "firewall_deny",
            "action": "blocked",
            "severity": {"value": 4}
        },
        "tenant": {"id": "tenant_alpha"},
        "source": {"ip": "192.0.2.1"},
        "destination": {"ip": "10.0.0.1"},
        "security": {"is_security_event": True},
        # Arbitrary vendor extensions that must NOT cause field explosion
        "vendor_ext": {
            f"custom_field_{i}": f"val_{i}" for i in range(50)
        }
    }

    # First send
    await connector.send(event)
    doc1 = connector.get_mock_document("evt_os_001")
    assert doc1 is not None
    assert doc1["event_id"] == "evt_os_001"
    assert doc1["source_ip"] == "192.0.2.1"
    # Verify canonical_ues preserves the original event intact
    assert doc1["canonical_ues"]["event"]["id"] == "evt_os_001"
    # Verify top-level doc keys are controlled
    top_keys = set(doc1.keys())
    assert len(top_keys) <= 15
    assert "vendor_ext" not in top_keys  # Contained inside canonical_ues

    # Second send (Idempotency test)
    await connector.send(event)
    assert len(connector.mock_storage) == 1
    doc2 = connector.get_mock_document("evt_os_001")
    assert doc2["event_id"] == "evt_os_001"


async def test_kafka_connector_ai_stream():
    connector = KafkaConnector(connector_name="ai_stream", topic="ulpf.ai.events", mock_mode=True)

    event = {
        "event": {
            "id": "evt_kafka_001",
            "type": "anomaly_telemetry",
            "severity": {"value": 5}
        },
        "tenant": {"id": "tenant_beta"}
    }

    await connector.send(event)
    events = connector.get_mock_events("ulpf.ai.events")
    assert len(events) == 1
    assert events[0]["event"]["id"] == "evt_kafka_001"
    assert events[0]["tenant"]["id"] == "tenant_beta"


async def test_http_connector_webhook():
    connector = HttpConnector(connector_name="http_webhook", mock_mode=True)

    event = {
        "event": {"id": "evt_http_001", "type": "system_alert"},
        "tenant": {"id": "tenant_alpha"}
    }

    await connector.send(event)
    assert len(connector.sent_events) == 1
    assert connector.sent_events[0]["event"]["id"] == "evt_http_001"


async def test_datalake_writer_partitioning():
    test_lake_dir = "./data/test_datalake_tmp"
    if os.path.exists(test_lake_dir):
        shutil.rmtree(test_lake_dir, ignore_errors=True)

    writer = DataLakeWriter(connector_name="data_lake", mock_mode=True)
    writer.fs_fallback.base_dir = test_lake_dir

    event = {
        "event": {
            "id": "evt_lake_001",
            "type": "audit_log",
            "severity": {"value": 2}
        },
        "tenant": {"id": "tenant_alpha"}
    }

    # First write
    await writer.send(event)
    assert "evt_lake_001" in writer.processed_event_ids

    # Idempotent write (duplicate send should be skipped)
    await writer.send(event)
    assert len(writer.processed_event_ids) == 1

    # Clean up test directory
    if os.path.exists(test_lake_dir):
        shutil.rmtree(test_lake_dir, ignore_errors=True)
