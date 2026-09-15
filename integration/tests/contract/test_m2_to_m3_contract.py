"""
Executable Contract Test: M2 -> M3 Boundary.
Verifies M2M3Adapter against REAL M2 and M3 schemas without mocks.
"""

import pytest
from integration.adapters.m2_m3_adapter import M2M3Adapter
from integration.contracts.tenant_context import TenantContext
from integration.tests.module_loader import get_m2_parsed_event_model, get_m3_parsed_event_model

M2ParsedEvent = get_m2_parsed_event_model()
M3ParsedEvent = get_m3_parsed_event_model()


def test_m2_to_m3_contract_transformation():
    """
    Given a real M2 ParsedEvent output:
    M2M3Adapter must produce a dictionary that strictly validates against M3 ParsedEvent input schema.
    """
    m2_real_output = {
        "schema_version": "1.0.0",
        "raw_event_id": "raw-cisco-asa-001234",
        "tenant_id": "tenant-cisco",
        "source_id": "cisco-asa-fw01",
        "status": "PARSED",
        "classification": {
            "format": "syslog",
            "vendor": "Cisco",
            "product": "ASA",
            "confidence": 0.99,
        },
        "parser": {
            "id": "parser-cisco-asa",
            "name": "Cisco ASA Parser",
            "version": "1.2.0",
            "confidence": 0.99,
        },
        "fields": {
            "timestamp": "2026-09-14T10:00:00Z",
            "srcip": "192.168.10.25",
            "dstip": "8.8.8.8",
            "srcport": 51542,
            "dstport": 443,
            "action": "allow",
            "message_id": "302013",
            "connection_id": "847392",
        },
        "unmapped_fields": [],
        "raw_reference": "raw/tenant-cisco/2026/09/14/raw-cisco-asa-001234.log",
        "sha256": "b4a8e833446059c99d0e9a3bdf0136274e1d670f59223fa8c9f041d8e11a3780",
        "processing_time_ms": 0.45,
        "metadata": {},
    }

    # Verify input conforms to M2 contract
    m2_obj = M2ParsedEvent(**m2_real_output)
    assert m2_obj.status == "PARSED"

    # Adapt M2 -> M3
    adapted = M2M3Adapter.adapt(m2_real_output)

    # Verify output conforms to M3 contract
    m3_obj = M3ParsedEvent(**adapted)

    assert m3_obj.raw_event_id == "raw-cisco-asa-001234"
    assert m3_obj.fields["srcip"] == "192.168.10.25"
    assert m3_obj.fields["dstip"] == "8.8.8.8"
    assert m3_obj.classification.vendor == "Cisco"
    assert m3_obj.classification.product == "ASA"
    assert m3_obj.parser.id == "parser-cisco-asa"
    
    # Verify nested integrity mapping
    assert m3_obj.integrity["hash"]["value"] == "b4a8e833446059c99d0e9a3bdf0136274e1d670f59223fa8c9f041d8e11a3780"
    assert m3_obj.integrity["hash"]["algorithm"] in ("SHA-256", "sha256")
    assert m3_obj.integrity["raw_hash"] == "b4a8e833446059c99d0e9a3bdf0136274e1d670f59223fa8c9f041d8e11a3780"

    # Verify nested raw storage reference mapping
    assert m3_obj.raw["storage_ref"] == "raw/tenant-cisco/2026/09/14/raw-cisco-asa-001234.log"
    assert m3_obj.raw["format"] == "syslog"


def test_m2_to_m3_contract_preserves_tenant():
    """Verify tenant_id is preserved across M2 to M3 boundary."""
    ctx = TenantContext(tenant_id="tenant-custom", source_id="src-custom")
    m2_data = {
        "raw_event_id": "raw-999",
        "fields": {"action": "deny"},
    }
    adapted = M2M3Adapter.adapt(m2_data, tenant_context=ctx)
    assert adapted["tenant_id"] == "tenant-custom"
    assert adapted["source_id"] == "src-custom"
