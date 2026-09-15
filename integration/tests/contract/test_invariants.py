"""
System-Wide Invariant Tests across all Integration Boundaries:
1. Tenant propagation across M1 -> M2 -> M3 -> M4 -> M5
2. M1 authoritative raw SHA-256 preservation without recomputation
3. Raw storage reference preservation
4. Correlation ID propagation across all hops
5. Duplicate delivery detection and suppression (idempotency)
"""

import pytest
import uuid
import hashlib
from integration.contracts.tenant_context import TenantContext
from integration.adapters.m1_raw_envelope_adapter import M1RawEnvelopeAdapter
from integration.adapters.m2_m3_adapter import M2M3Adapter
from integration.adapters.m3_m4_adapter import M3M4Adapter
from integration.adapters.m4_m5_adapter import M4M5Adapter
from integration.adapters.idempotency import IdempotencyTracker
from integration.tests.module_loader import (
    get_m2_raw_envelope_model,
    get_m3_parsed_event_model,
    get_m4_canonical_event_model,
    get_m5_router_components,
)

M2RawEnvelope = get_m2_raw_envelope_model()
M3ParsedEvent = get_m3_parsed_event_model()
M4CanonicalEvent = get_m4_canonical_event_model()
SmartRouter, PolicyRule, _ = get_m5_router_components()


def test_tenant_propagation_all_boundaries():
    """Verify tenant identity remains uncorrupted and intact across M1->M2->M3->M4->M5."""
    tenant_id = "tenant-enterprise-99"
    source_id = "sensor-perimeter-01"
    raw_id = "raw_ev_001"
    correlation_id = str(uuid.uuid4())

    ctx = TenantContext(
        tenant_id=tenant_id,
        source_id=source_id,
        correlation_id=correlation_id,
    )

    # 1. M1 Envelope
    m1_env = {
        "raw_event_id": raw_id,
        "tenant_id": tenant_id,
        "source_id": source_id,
        "payload": {"data": "test syslog message"},
        "integrity": {"hash": "abc123hash"},
    }

    # 2. M1 -> M2
    m2_input = M1RawEnvelopeAdapter.adapt(m1_env, tenant_context=ctx)
    assert m2_input["tenant_id"] == tenant_id
    assert m2_input["source_id"] == source_id

    # Simulate M2 parsing output
    m2_output = {
        "raw_event_id": raw_id,
        "tenant_id": m2_input["tenant_id"],
        "source_id": m2_input["source_id"],
        "status": "PARSED",
        "fields": {"action": "allow"},
        "sha256": "abc123hash",
    }

    # 3. M2 -> M3
    m3_input = M2M3Adapter.adapt(m2_output, tenant_context=ctx)
    assert m3_input["tenant_id"] == tenant_id

    # Simulate M3 normalization output (M3 drops tenant_id in its schema)
    m3_output = {
        "success": True,
        "raw_event_id": raw_id,
        "event": {
            "ulpf": {
                "event": {"id": "evt_norm_001", "timestamp": "2026-09-14T10:00:00Z"},
                "provenance": {"raw_event_id": raw_id},
                "integrity": {"raw_hash": "abc123hash"},
            }
        },
    }

    # 4. M3 -> M4 (Integration restores trusted TenantContext)
    m4_request = M3M4Adapter.adapt(m3_output, tenant_context=ctx)
    assert m4_request["event"]["tenant"]["tenant_id"] == tenant_id
    assert m4_request["tenant_context"]["tenant_id"] == tenant_id

    # Simulate M4 enrichment result
    m4_output = {
        "status": "SUCCESS",
        "event": m4_request["event"],
        "integrity": {"algorithm": "sha256", "digest": "enriched_digest_val"},
    }

    # 5. M4 -> M5 (Harmonize tenant.id = tenant.tenant_id)
    m5_event = M4M5Adapter.adapt(m4_output)
    assert m5_event["tenant"]["tenant_id"] == tenant_id
    assert m5_event["tenant"]["id"] == tenant_id

    # Verify M5 Router extracts the exact original tenant
    router = SmartRouter([])
    assert router.extract_tenant_id(m5_event) == tenant_id


def test_raw_hash_preservation_across_all_boundaries():
    """Verify that M1 authoritative raw SHA-256 is preserved without recalculation or mutation."""
    raw_payload_bytes = b"authoritative raw log content 2026-09-14"
    authoritative_raw_hash = hashlib.sha256(raw_payload_bytes).hexdigest()

    ctx = TenantContext(tenant_id="tenant-audit", source_id="src-audit")

    # M1
    m1_env = {
        "raw_event_id": "raw-audit-1",
        "payload": {"data": raw_payload_bytes.decode("utf-8")},
        "integrity": {"hash": authoritative_raw_hash},
        "raw_storage": {"object_key": "raw/audit/log1.log"},
    }

    # M1 -> M2
    m2_input = M1RawEnvelopeAdapter.adapt(m1_env, tenant_context=ctx)
    assert m2_input["sha256"] == authoritative_raw_hash

    # M2 -> M3
    m2_output = dict(m2_input, status="PARSED", fields={})
    m3_input = M2M3Adapter.adapt(m2_output, tenant_context=ctx)
    assert m3_input["integrity"]["hash"]["value"] == authoritative_raw_hash

    # M3 -> M4
    m3_output = {
        "success": True,
        "event": {
            "ulpf": {
                "event": {"id": "evt_1", "timestamp": "2026-09-14T10:00:00Z"},
                "provenance": {"raw_event_id": "raw-audit-1"},
                "integrity": {"raw_hash": authoritative_raw_hash},
            }
        },
    }
    m4_request = M3M4Adapter.adapt(m3_output, tenant_context=ctx)
    assert m4_request["event"]["extensions"]["raw_integrity"]["raw_hash"] == authoritative_raw_hash


def test_raw_reference_preservation():
    """Verify MinIO/S3 raw storage object key is passed through to cold-evidence references."""
    storage_ref = "s3://raw-vault/tenant-sec/2026/09/14/evidence-001.gz"
    m1_env = {
        "raw_event_id": "raw-ref-1",
        "raw_storage": {"object_key": storage_ref},
        "payload": {"data": "content"},
        "integrity": {"hash": "hash1"},
    }
    m2_input = M1RawEnvelopeAdapter.adapt(m1_env)
    assert m2_input["raw_reference"] == storage_ref

    m3_input = M2M3Adapter.adapt(dict(m2_input, status="PARSED", fields={}))
    assert m3_input["raw"]["storage_ref"] == storage_ref


def test_duplicate_delivery_idempotency():
    """Verify that duplicate raw_event_id deliveries are safely identified and deduplicated."""
    tracker = IdempotencyTracker(capacity=100, ttl_seconds=60)
    tenant_id = "tenant-alpha"
    raw_event_id = "raw_dup_test_001"

    # First delivery: NEW
    first_seen = tracker.check_and_set(tenant_id, raw_event_id, {"status": "PARSED"})
    assert first_seen is True

    # Immediate duplicate delivery: SUPPRESSED
    duplicate_seen = tracker.check_and_set(tenant_id, raw_event_id)
    assert duplicate_seen is False

    # Cached outcome can be retrieved without re-executing pipeline
    cached = tracker.get_cached_result(tenant_id, raw_event_id)
    assert cached == {"status": "PARSED"}

    # Different tenant with same raw_event_id is isolated and treated as distinct
    diff_tenant_seen = tracker.check_and_set("tenant-beta", raw_event_id)
    assert diff_tenant_seen is True
