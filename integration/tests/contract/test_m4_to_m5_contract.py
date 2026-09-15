"""
Executable Contract Test: M4 -> M5 Boundary.
Verifies M4M5Adapter against REAL M4 EnrichmentResult and M5 SmartRouter policies.
Resolves P1-2 (tenant key mismatch: tenant.tenant_id vs tenant.id).
"""

import pytest
from integration.adapters.m4_m5_adapter import M4M5Adapter
from integration.tests.module_loader import (
    get_m4_enrichment_request_model,
    get_m5_router_components,
)

_, M4EnrichmentResult = get_m4_enrichment_request_model()
SmartRouter, PolicyRule, RoutingDecision = get_m5_router_components()


def test_m4_to_m5_contract_resolves_p1_2():
    """
    Given an M4 EnrichmentResult:
      - Contains 'tenant.tenant_id'
      - Wrapped in EnrichmentResult container
    M4M5Adapter must:
      1. Unwrap 'result.event' (M5 expects canonical event, not the wrapper)
      2. Harmonize 'tenant.id = tenant.tenant_id' while preserving 'tenant.tenant_id'
      3. Enable M5 SmartRouter to extract tenant_id and evaluate tenant-scoped policy rules
    """
    # Real output shape from M4 POST /v1/enrich
    m4_real_result = {
        "status": "SUCCESS",
        "event": {
            "schema_version": "ues.v1",
            "event": {
                "id": "EVT-CISCO-001234",
                "timestamp": "2026-09-14T10:00:00Z",
                "kind": "event",
                "type": ["network"],
                "category": ["network"],
                "outcome": "success",
            },
            "source": {"ip": "192.168.10.25", "port": 51542},
            "destination": {"ip": "8.8.8.8", "port": 443},
            "network": {"transport": "tcp", "protocol": "https"},
            "provenance": {"raw_event_id": "raw-cisco-asa-001234"},
            "tenant": {
                "tenant_id": "tenant-cisco",  # M4 canonical key
            },
            "extensions": {
                "geo_location": {"country": "US", "city": "Dallas"},
            },
        },
        "provenance": [
            {
                "provider_id": "geoip-local",
                "provider_version": "1.0.0",
                "enrichment_type": "geo_ip",
                "confidence": 0.95,
                "result_status": "SUCCESS",
                "cache_status": "HIT",
            }
        ],
        "diagnostics": {
            "total_duration_ms": 2.5,
        },
        "integrity": {
            "algorithm": "sha256",
            "digest": "ccddeeff00112233445566778899aabbccddeeff00112233445566778899aabb",
            "canonicalization": "rfc8785",
            "phase": "post_enrichment",
        },
    }

    # Verify input conforms to M4 EnrichmentResult contract
    m4_obj = M4EnrichmentResult(**m4_real_result)
    assert m4_obj.status.value == "SUCCESS"

    # Adapt M4 -> M5
    m5_event = M4M5Adapter.adapt(m4_real_result)

    # Invariants verification
    assert m5_event["schema_version"] == "ues.v1"
    assert m5_event["tenant"]["tenant_id"] == "tenant-cisco"
    assert m5_event["tenant"]["id"] == "tenant-cisco"  # P1-2 resolved
    assert m5_event["tenant_id"] == "tenant-cisco"      # Root fallback populated
    assert m5_event["integrity"]["digest"] == "ccddeeff00112233445566778899aabbccddeeff00112233445566778899aabb"

    # Verify M5 SmartRouter extracts tenant successfully
    rules = [
        # Tenant-scoped rule: only fires for 'tenant-cisco'
        PolicyRule(
            id="rule_cisco_siem",
            name="Cisco SIEM Route",
            tenant_id="tenant-cisco",
            destinations=["cisco_splunk_cluster"],
            priority=100,
        ),
        # Global fallback rule
        PolicyRule(
            id="rule_archive",
            name="Default Cold Archive",
            destinations=["cold_storage_s3"],
            priority=10,
        ),
    ]

    router = SmartRouter(rules)
    extracted_tenant = router.extract_tenant_id(m5_event)
    assert extracted_tenant == "tenant-cisco", "SmartRouter failed to extract tenant_id due to P1-2 key mismatch"

    destinations, decision = router.route(m5_event)
    assert "cisco_splunk_cluster" in destinations
    assert "cold_storage_s3" in destinations
    assert decision.tenant_id == "tenant-cisco"
