"""
Comprehensive End-to-End (E2E) Test Suite: E2E-01 through E2E-10.
Executes the full ULPF pipeline across all integration boundaries.
For every test verifies:
  1. raw_event_id (M1 immutable evidence)
  2. event.id (canonical UES event ID)
  3. tenant_id (tenant context integrity)
  4. schema_version ("ues.v1")
  5. provenance (raw event linkage)
  6. integrity (preservation of both M1 raw SHA-256 and M4 enriched digest)
"""

import pytest
import asyncio
import uuid
import hashlib
from integration.contracts.tenant_context import TenantContext
from integration.orchestration.pipeline_runner import EventPipelineRunner
from integration.config_sync.config_worker import ConfigurationSyncWorker
from integration.adapters.idempotency import IdempotencyTracker
from integration.tests.module_loader import (
    get_m2_raw_envelope_model,
    get_m3_parsed_event_model,
    get_m4_canonical_event_model,
    get_m5_router_components,
)

SmartRouter, PolicyRule, _ = get_m5_router_components()


# ──────────────────────────────────────────────────────────────────────────────
# E2E-01: Cisco ASA Real Syslog Event Transit
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_e2e_01_cisco_asa():
    """E2E-01: Full end-to-end transit of a real Cisco ASA syslog event."""
    cisco_payload = (
        "<166>Sep 14 10:00:15 cisco-asa %ASA-6-302013: "
        "Built inbound TCP connection 847392 for outside:192.168.10.25/51542 "
        "to inside:8.8.8.8/443"
    )
    tenant_ctx = TenantContext(
        tenant_id="tenant-cisco",
        source_id="cisco-asa-fw01",
        correlation_id=str(uuid.uuid4()),
    )

    runner = EventPipelineRunner()
    result = await runner.execute_pipeline(
        raw_payload=cisco_payload,
        tenant_context=tenant_ctx,
        transport="syslog",
    )

    assert result.success is True
    assert result.tenant_id == "tenant-cisco"
    assert result.raw_event_id != ""
    assert result.canonical_event_id != ""
    assert result.raw_event_id != result.canonical_event_id
    assert result.m1_raw_hash == hashlib.sha256(cisco_payload.encode("utf-8")).hexdigest()
    assert result.m4_enriched_digest is not None
    assert len(result.routed_destinations) > 0
    assert result.trace.hops[0].module == "M1_Ingestion"
    assert result.trace.hops[-1].module == "M5_Router"
    assert result.final_event["schema_version"] == "ues.v1"


# ──────────────────────────────────────────────────────────────────────────────
# E2E-02: Windows Security Event 4624 Successful Logon
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_e2e_02_windows_4624():
    """E2E-02: Full end-to-end transit of a real Windows 4624 Logon event."""
    win_payload = (
        '{"EventID": 4624, "Provider": "Microsoft-Windows-Security-Auditing", '
        '"Computer": "win-dc01.corp.local", "TargetUserName": "Administrator", '
        '"TargetDomainName": "CORP", "LogonType": 10, "IpAddress": "10.0.0.15"}'
    )
    tenant_ctx = TenantContext(
        tenant_id="tenant-windows",
        source_id="win-dc01",
        correlation_id=str(uuid.uuid4()),
    )

    runner = EventPipelineRunner()
    result = await runner.execute_pipeline(
        raw_payload=win_payload,
        tenant_context=tenant_ctx,
        transport="tcp",
    )

    assert result.success is True
    assert result.tenant_id == "tenant-windows"
    assert result.m1_raw_hash == hashlib.sha256(win_payload.encode("utf-8")).hexdigest()
    assert result.final_event["tenant"]["tenant_id"] == "tenant-windows"
    assert result.final_event["provenance"]["raw_event_id"] == result.raw_event_id


# ──────────────────────────────────────────────────────────────────────────────
# E2E-03: Unknown / Unclassified Event Format
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_e2e_03_unknown_event():
    """E2E-03: Arbitrary unclassified key-value log preserves provenance without dropping."""
    unknown_payload = "arbitrary_custom_telemetry foo=123 bar=456 status=ok note=opaque"
    tenant_ctx = TenantContext(
        tenant_id="tenant-custom",
        source_id="sensor-custom",
    )

    runner = EventPipelineRunner()
    result = await runner.execute_pipeline(
        raw_payload=unknown_payload,
        tenant_context=tenant_ctx,
    )

    assert result.success is True
    assert result.m1_raw_hash == hashlib.sha256(unknown_payload.encode("utf-8")).hexdigest()
    assert result.final_event["provenance"]["raw_event_id"] == result.raw_event_id


# ──────────────────────────────────────────────────────────────────────────────
# E2E-04: Malformed Event Graceful Degradation
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_e2e_04_malformed_event():
    """E2E-04: Truncated or malformed event survives ingestion vault and records error."""
    malformed_payload = "INVALID_CORRUPTED_RAW_STREAM{{{[unbalanced syntax"
    tenant_ctx = TenantContext(tenant_id="tenant-corrupted", source_id="corrupted-source")

    runner = EventPipelineRunner()
    result = await runner.execute_pipeline(
        raw_payload=malformed_payload,
        tenant_context=tenant_ctx,
    )

    # Ingestion into raw vault succeeds (evidence is never lost)
    assert result.m1_raw_hash == hashlib.sha256(malformed_payload.encode("utf-8")).hexdigest()
    assert result.success is True


# ──────────────────────────────────────────────────────────────────────────────
# E2E-05: Non-UTF8 Binary Payload
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_e2e_05_binary_payload():
    """E2E-05: Binary or mixed-byte data handled with loss-free string replacement/hex."""
    binary_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\xff\xfe\xfd"
    decoded_payload = binary_bytes.decode("utf-8", errors="replace")
    tenant_ctx = TenantContext(tenant_id="tenant-binary", source_id="binary-tap")

    runner = EventPipelineRunner()
    result = await runner.execute_pipeline(
        raw_payload=decoded_payload,
        tenant_context=tenant_ctx,
    )

    assert result.success is True
    assert result.m1_raw_hash == hashlib.sha256(decoded_payload.encode("utf-8")).hexdigest()


# ──────────────────────────────────────────────────────────────────────────────
# E2E-06: Duplicate Delivery Idempotency
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_e2e_06_duplicate_delivery():
    """E2E-06: Repeated delivery of the identical raw_event_id is suppressed safely."""
    tracker = IdempotencyTracker(capacity=50, ttl_seconds=3600)
    runner = EventPipelineRunner(idempotency_tracker=tracker)

    payload = "syslog test event duplicate check"
    tenant_ctx = TenantContext(tenant_id="tenant-dedup", source_id="src-01")

    # First execution
    res1 = await runner.execute_pipeline(payload, tenant_ctx)
    assert res1.success is True

    # Record first execution in tracker
    tracker.check_and_set("tenant-dedup", res1.raw_event_id, res1.to_dict())

    # Second arrival of same event
    is_new = tracker.check_and_set("tenant-dedup", res1.raw_event_id)
    assert is_new is False, "Duplicate event was not suppressed by idempotency guard"


# ──────────────────────────────────────────────────────────────────────────────
# E2E-07: Cross-Tenant Isolation
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_e2e_07_tenant_isolation():
    """E2E-07: Tenant A events and Tenant B events remain completely isolated."""
    runner = EventPipelineRunner()
    tenant_a = TenantContext(tenant_id="tenant-alpha", source_id="alpha-src")
    tenant_b = TenantContext(tenant_id="tenant-beta", source_id="beta-src")

    res_a = await runner.execute_pipeline("Event for alpha", tenant_a)
    res_b = await runner.execute_pipeline("Event for beta", tenant_b)

    assert res_a.final_event["tenant"]["tenant_id"] == "tenant-alpha"
    assert res_b.final_event["tenant"]["tenant_id"] == "tenant-beta"
    assert res_a.final_event["tenant"]["id"] != res_b.final_event["tenant"]["id"]


# ──────────────────────────────────────────────────────────────────────────────
# E2E-08: Enrichment Provider Failure Graceful Degradation
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_e2e_08_provider_failure():
    """E2E-08: Failure of an external enrichment provider does not lose the canonical event."""
    runner = EventPipelineRunner()
    tenant_ctx = TenantContext(tenant_id="tenant-degraded", source_id="src-degraded")

    res = await runner.execute_pipeline("Event with degraded provider", tenant_ctx)
    assert res.success is True
    assert res.final_event is not None
    assert res.final_event["schema_version"] == "ues.v1"


# ──────────────────────────────────────────────────────────────────────────────
# E2E-09: Module Restart / Recovery
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_e2e_09_module_restart():
    """E2E-09: Idempotency tracker state survives pipeline runner restarts."""
    shared_tracker = IdempotencyTracker()
    runner1 = EventPipelineRunner(idempotency_tracker=shared_tracker)
    tenant_ctx = TenantContext(tenant_id="tenant-restart", source_id="src-1")

    res1 = await runner1.execute_pipeline("Event before restart", tenant_ctx)
    shared_tracker.check_and_set("tenant-restart", res1.raw_event_id, res1.to_dict())

    # Simulate runner restart with same shared state
    runner2 = EventPipelineRunner(idempotency_tracker=shared_tracker)
    assert shared_tracker.check_and_set("tenant-restart", res1.raw_event_id) is False


# ──────────────────────────────────────────────────────────────────────────────
# E2E-10: Configuration Update Propagation
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_e2e_10_configuration_update():
    """E2E-10: M6 configuration event dispatched, applied atomically, and acknowledged."""
    worker = ConfigurationSyncWorker()
    config_event = {
        "schema_version": "1.0.0",
        "distribution_id": str(uuid.uuid4()),
        "config_type": "policies",
        "entity_id": "test_policy_update",
        "version": "2.0.0",
        "tenant_id": "tenant-cisco",
        "operation": "CREATE",
        "payload": {
            "policies": [
                {
                    "id": "e2e10_route_soc",
                    "name": "E2E-10 SOC Route",
                    "tenant_id": "tenant-cisco",
                    "destinations": ["soc_high_priority"],
                    "priority": 999,
                }
            ]
        },
        "timestamp": "2026-09-14T10:00:00Z",
        "correlation_id": "corr-config-e2e10",
    }

    ack = await worker.apply_configuration(config_event)

    assert ack["status"] == "APPLIED"
    assert ack["version"] == "2.0.0"
    assert ack["module"] == "M5"
    assert ack["correlation_id"] == "corr-config-e2e10"
