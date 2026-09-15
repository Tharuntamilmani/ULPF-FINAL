"""
Executable Contract Test: M3 -> M4 Boundary.
Verifies M3M4Adapter against REAL M3 NormalizationResult and M4 CanonicalEvent schemas.
Resolves P0-2 (root mismatch) and P1-1 (tenant metadata loss).
"""

import pytest
from integration.adapters.m3_m4_adapter import M3M4Adapter
from integration.contracts.tenant_context import TenantContext
from integration.tests.module_loader import (
    get_m3_normalization_result_model,
    get_m4_canonical_event_model,
    get_m4_enrichment_request_model,
)

M3NormalizationResult = get_m3_normalization_result_model()
M4CanonicalEvent = get_m4_canonical_event_model()
M4EnrichmentRequest, M4EnrichmentResult = get_m4_enrichment_request_model()


def test_m3_to_m4_contract_resolves_p0_2_and_p1_1():
    """
    Given a real M3 NormalizationResult with outer 'event.ulpf' wrapper and missing tenant:
    M3M4Adapter must:
      1. Unwrap 'event.ulpf' to flat CanonicalEvent (P0-2)
      2. Restore trusted TenantContext (P1-1)
      3. Set schema_version = 'ues.v1'
      4. Strictly satisfy M4 CanonicalEvent schema with extra='forbid'
    """
    # Real output shape emitted by M3 POST /v1/normalize
    m3_real_output = {
        "success": True,
        "raw_event_id": "raw-cisco-asa-001234",
        "event": {
            "ulpf": {
                "schema": {"version": "1.0.0", "specification": "UES"},
                "event": {
                    "id": "EVT-CISCO-001234",
                    "timestamp": "2026-09-14T10:00:00Z",
                    "kind": "event",
                    "type": ["network", "connection"],
                    "category": ["network"],
                    "outcome": "success",
                },
                "observer": {
                    "hostname": "sensor-01",
                    "ip": "192.168.1.1",
                    "type": "firewall",
                    "version": "9.18",
                },
                "source": {
                    "ip": "192.168.10.25",
                    "port": 51542,
                },
                "destination": {
                    "ip": "8.8.8.8",
                    "port": 443,
                },
                "network": {
                    "transport": "tcp",
                    "protocol": "https",
                    "direction": "outbound",
                    "bytes_in": 1024,
                    "bytes_out": 2048,
                },
                "host": {
                    "name": "cisco-asa-edge",
                },
                "identity": {},
                "application": {
                    "name": "https",
                },
                "process": {},
                "security": {
                    "severity": "informational",
                },
                "parser": {
                    "id": "parser-cisco-asa",
                    "name": "Cisco ASA Parser",
                    "version": "1.2.0",
                },
                "normalization": {
                    "schema_target": "ues.v1",
                    "rule_version": "1.0.0",
                },
                "provenance": {
                    "raw_event_id": "raw-cisco-asa-001234",
                },
                "integrity": {
                    "raw_hash": "b4a8e833446059c99d0e9a3bdf0136274e1d670f59223fa8c9f041d8e11a3780",
                    "hash": {
                        "algorithm": "sha256",
                        "value": "b4a8e833446059c99d0e9a3bdf0136274e1d670f59223fa8c9f041d8e11a3780",
                    },
                },
                "raw": {
                    "storage_ref": "raw/tenant-cisco/2026/09/14/raw-cisco-asa-001234.log",
                    "format": "syslog",
                },
                "vendor": {
                    "vendor_id": "cisco",
                    "product": "asa",
                },
            }
        },
        "errors": [],
        "normalization": {"status": "SUCCESS"},
    }

    # Verify input conforms to M3 NormalizationResult contract
    m3_norm_obj = M3NormalizationResult(**m3_real_output)
    assert m3_norm_obj.success is True

    # Trusted tenant context carried alongside event
    trusted_ctx = TenantContext(
        tenant_id="tenant-cisco",
        source_id="cisco-asa-fw01",
        correlation_id="corr-trace-001",
    )

    # Adapt M3 -> M4
    adapted_request = M3M4Adapter.adapt(
        m3_result=m3_real_output,
        tenant_context=trusted_ctx,
    )

    # 1. Verify CanonicalEvent passes M4 Pydantic validation (extra='forbid')
    canonical_event = M4CanonicalEvent(**adapted_request["event"])

    # Invariants verification
    assert canonical_event.schema_version == "ues.v1"
    assert canonical_event.event.id == "EVT-CISCO-001234"
    assert canonical_event.provenance.raw_event_id == "raw-cisco-asa-001234"
    assert canonical_event.tenant.tenant_id == "tenant-cisco"
    assert canonical_event.source.ip == "192.168.10.25"
    assert canonical_event.destination.ip == "8.8.8.8"
    assert canonical_event.network.transport == "tcp"

    # Verify raw integrity preservation in extensions
    raw_integ = canonical_event.extensions.get("raw_integrity")
    assert raw_integ is not None
    assert raw_integ["raw_hash"] == "b4a8e833446059c99d0e9a3bdf0136274e1d670f59223fa8c9f041d8e11a3780"

    # 2. Verify complete M4 EnrichmentRequest passes validation
    enrichment_req = M4EnrichmentRequest(**adapted_request)
    assert enrichment_req.tenant_context.tenant_id == "tenant-cisco"


def test_m3_to_m4_contract_rejects_missing_tenant_context():
    """Fails safely if tenant context is missing, since M3 does not carry tenant."""
    m3_real_output = {
        "success": True,
        "event": {
            "ulpf": {
                "event": {"id": "EVT-1", "timestamp": "2026-09-14T10:00:00Z"},
                "provenance": {"raw_event_id": "RAW-1"},
            }
        }
    }
    with pytest.raises(ValueError, match="no trusted TenantContext was supplied"):
        M3M4Adapter.adapt(m3_real_output, tenant_context=None)  # type: ignore
