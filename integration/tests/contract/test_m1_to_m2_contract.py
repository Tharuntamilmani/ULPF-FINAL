"""
Executable Contract Test: M1 -> M2 Boundary.
Verifies M1RawEnvelopeAdapter against REAL M1 and M2 schemas without mocks.
"""

import pytest
from integration.adapters.m1_raw_envelope_adapter import M1RawEnvelopeAdapter
from integration.contracts.tenant_context import TenantContext
from integration.tests.module_loader import get_m2_raw_envelope_model

M2RawEnvelope = get_m2_raw_envelope_model()


def test_m1_to_m2_contract_transformation():
    """
    Given a real M1 RawEventEnvelope with nested structures:
      payload.data, transport.protocol, integrity.hash, raw_storage.object_key
    M1RawEnvelopeAdapter must produce a flat dictionary that strictly validates against M2 RawEventEnvelope.
    """
    m1_real_serialized = {
        "schema_version": "1.0.0",
        "raw_event_id": "raw-cisco-asa-001234",
        "tenant_id": "tenant-cisco",
        "source_id": "cisco-asa-fw01",
        "received_at": "2026-09-14T10:00:00Z",
        "transport": {
            "protocol": "syslog",
            "client_ip": "192.168.1.50",
            "port": 514
        },
        "payload": {
            "data": "<166>Sep 14 10:00:00 asa %ASA-6-302013: Built outbound TCP connection 998811 for outside:1.1.1.1/443 (1.1.1.1/443) to inside:192.168.1.100/54321",
            "encoding": "utf-8",
            "size_bytes": 145
        },
        "integrity": {
            "algorithm": "sha256",
            "hash": "b4a8e833446059c99d0e9a3bdf0136274e1d670f59223fa8c9f041d8e11a3780"
        },
        "raw_storage": {
            "vault": "minio",
            "bucket": "ulpf-raw-vault",
            "object_key": "raw/tenant-cisco/2026/09/14/raw-cisco-asa-001234.log"
        },
        "metadata": {"collector": "edge-agent-01"}
    }

    # Execute Adapter
    adapted = M1RawEnvelopeAdapter.adapt(m1_real_serialized)

    # Verify M2 Pydantic Validation succeeds without errors
    m2_envelope = M2RawEnvelope(**adapted)

    # Invariants verification
    assert m2_envelope.raw_event_id == "raw-cisco-asa-001234"
    assert m2_envelope.tenant_id == "tenant-cisco"
    assert m2_envelope.source_id == "cisco-asa-fw01"
    assert m2_envelope.transport == "syslog"
    assert m2_envelope.payload.startswith("<166>Sep 14")
    assert m2_envelope.encoding == "utf-8"
    assert m2_envelope.sha256 == "b4a8e833446059c99d0e9a3bdf0136274e1d670f59223fa8c9f041d8e11a3780"
    assert m2_envelope.raw_reference == "raw/tenant-cisco/2026/09/14/raw-cisco-asa-001234.log"


def test_m1_to_m2_contract_preserves_raw_hash_authoritative():
    """Verify that M1RawEnvelopeAdapter NEVER alters or re-calculates the authoritative M1 SHA-256 hash."""
    authoritative_hash = "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff"
    m1_data = {
        "raw_event_id": "raw-001",
        "tenant_id": "tenant-test",
        "transport": {"protocol": "http"},
        "payload": {"data": "test payload", "encoding": "utf-8"},
        "integrity": {"hash": authoritative_hash},
        "raw_storage": {"object_key": "raw/ref.log"},
    }

    adapted = M1RawEnvelopeAdapter.adapt(m1_data)
    assert adapted["sha256"] == authoritative_hash


def test_m1_to_m2_contract_with_tenant_context():
    """Verify that trusted TenantContext is seamlessly injected."""
    ctx = TenantContext(
        tenant_id="tenant-enterprise",
        source_id="win-dc-01",
        authenticated_principal="agent-service",
        correlation_id="corr-9999",
    )
    m1_data = {
        "raw_event_id": "raw-002",
        "payload": {"data": "event log"},
        "integrity": {"hash": "abc"},
    }

    adapted = M1RawEnvelopeAdapter.adapt(m1_data, tenant_context=ctx)
    assert adapted["tenant_id"] == "tenant-enterprise"
    assert adapted["source_id"] == "win-dc-01"


def test_m1_to_m2_contract_rejects_missing_raw_event_id():
    """Adapter must fail safely if raw_event_id is absent."""
    with pytest.raises(ValueError, match="missing mandatory 'raw_event_id'"):
        M1RawEnvelopeAdapter.adapt({"payload": {"data": "invalid"}})
