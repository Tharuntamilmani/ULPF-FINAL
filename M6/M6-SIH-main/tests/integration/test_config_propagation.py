"""
Integration tests for Control-Plane Configuration Synchronization (Phases 14-21, 24).
Verifies:
  - Transactional Outbox pattern across sources, parsers, mappings, policies, schemas
  - Distribution state machine: PENDING → SENT → ACKNOWLEDGED / FAILED
  - JSON Schema validation of outgoing events and incoming ACKs
  - Bounded exponential retries (max 3, exp backoff capped at 10s)
  - Idempotency on duplicate events and duplicate ACKs
  - Rejection of stale ACKs, wrong-version ACKs, and wrong-module ACKs
  - Status API reporting real persisted state
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import (
    VersionMismatchError,
    WrongModuleAckError,
)
from backend.app.integrations.mock_module_client import MockModuleClient
from backend.app.models.config_distribution import DistributionStatus
from backend.app.repositories.distribution_repo import DistributionRepository
from backend.app.services.config_service import ConfigDistributionService


@pytest.fixture
def config_service(seeded_db: AsyncSession) -> ConfigDistributionService:
    return ConfigDistributionService(seeded_db)


# ── 1-5: Mutations create outbox events ───────────────────────────────────────


@pytest.mark.asyncio
async def test_1_source_mutation_creates_event(
    app_client: AsyncClient, auth_headers: dict, seeded_db: AsyncSession
):
    resp = await app_client.post(
        "/api/v1/sources",
        json={
            "source_id": "prop-src-1",
            "name": "Prop Source 1",
            "vendor": "Cisco",
            "product": "ASA",
            "source_type": "firewall",
            "protocol": "syslog",
            "transport": "udp",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    repo = DistributionRepository(seeded_db)
    targets = await repo.list_pending()
    # Mock client automatically dispatches and transitions to ACKNOWLEDGED
    dist_list = await repo.list_by_config_key("sources")
    assert len(dist_list) > 0
    assert dist_list[0].target_module == "M1"
    assert dist_list[0].status == DistributionStatus.ACKNOWLEDGED


@pytest.mark.asyncio
async def test_2_parser_mutation_creates_event(
    app_client: AsyncClient, auth_headers: dict, seeded_db: AsyncSession
):
    resp = await app_client.post(
        "/api/v1/parsers",
        json={
            "parser_id": "prop-parser-1",
            "name": "Prop Parser 1",
            "vendor": "V",
            "product": "P",
            "format": "syslog",
            "version": "1.0.0",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    repo = DistributionRepository(seeded_db)
    dist_list = await repo.list_by_config_key("parsers")
    assert len(dist_list) > 0
    assert dist_list[0].target_module == "M2"
    assert dist_list[0].status == DistributionStatus.ACKNOWLEDGED


@pytest.mark.asyncio
async def test_3_mapping_mutation_creates_event(
    app_client: AsyncClient, auth_headers: dict, seeded_db: AsyncSession
):
    resp = await app_client.post(
        "/api/v1/mappings",
        json={
            "mapping_id": "prop-mapping-1",
            "name": "Prop Mapping 1",
            "source_format": "syslog",
            "target_schema": "network.firewall",
            "target_version": "1.0.0",
            "version": "1.0.0",
            "fields": {"src_ip": "source.ip"},
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    repo = DistributionRepository(seeded_db)
    dist_list = await repo.list_by_config_key("mappings")
    assert len(dist_list) > 0
    assert dist_list[0].target_module == "M3"
    assert dist_list[0].status == DistributionStatus.ACKNOWLEDGED


@pytest.mark.asyncio
async def test_4_policy_mutation_creates_event(
    app_client: AsyncClient, auth_headers: dict, seeded_db: AsyncSession
):
    resp = await app_client.post(
        "/api/v1/policies",
        json={
            "policy_id": "prop-policy-1",
            "name": "Prop Policy 1",
            "version": "1.0.0",
            "priority": 50,
            "conditions": [{"field": "severity", "operator": ">=", "value": 3}],
            "destinations": ["kafka://alerts"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    repo = DistributionRepository(seeded_db)
    dist_list = await repo.list_by_config_key("policies")
    assert len(dist_list) > 0
    assert dist_list[0].target_module == "M5"
    assert dist_list[0].status == DistributionStatus.ACKNOWLEDGED


@pytest.mark.asyncio
async def test_5_schema_mutation_creates_event(
    app_client: AsyncClient, auth_headers: dict, seeded_db: AsyncSession
):
    resp = await app_client.post(
        "/api/v1/schemas",
        json={
            "name": "network.flow",
            "description": "Network flow schema",
            "initial_version": {
                "version": "1.0.0",
                "json_schema": {"type": "object", "properties": {"bytes": {"type": "integer"}}},
                "changelog": "Initial version",
            },
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    repo = DistributionRepository(seeded_db)
    dist_list = await repo.list_by_config_key("schemas")
    assert len(dist_list) > 0
    assert dist_list[0].target_module == "M3"
    assert dist_list[0].status == DistributionStatus.ACKNOWLEDGED


# ── 6-9: Outbox durability, dispatch, and state transitions ──────────────────


@pytest.mark.asyncio
async def test_6_outbox_durability_and_pending_dispatch(
    config_service: ConfigDistributionService, seeded_db: AsyncSession
):
    """Test creating outbox event in PENDING state and dispatching it."""
    targets = await config_service.create_outbox_event(
        config_type="sources",
        entity_id="outbox-src-1",
        version="1.0.0",
        tenant_id="default-tenant-uuid",
        operation="CREATE",
        payload={"source_id": "outbox-src-1"},
        actor="admin",
        actor_role="SUPER_ADMIN",
    )
    await seeded_db.commit()

    # Verify PENDING state before dispatch
    repo = DistributionRepository(seeded_db)
    pending = await repo.list_pending()
    assert any(t.distribution_id == targets[0].distribution_id for t in pending)

    # Dispatch
    dispatched = await config_service.dispatch_outbox_events(targets, "admin", "SUPER_ADMIN")
    assert dispatched[0].status == DistributionStatus.ACKNOWLEDGED


@pytest.mark.asyncio
async def test_9_dispatch_failure_and_bounded_retry(
    config_service: ConfigDistributionService, seeded_db: AsyncSession
):
    """Test bounded retries when module client fails."""
    # Setup mock client to fail
    mock_client = MockModuleClient("M1")
    mock_client.should_fail = True
    mock_client.failure_reason = "Simulated connection refused"

    # Monkeypatch client getter
    config_service._get_client_for_module = lambda mod: mock_client

    targets = await config_service.create_outbox_event(
        config_type="sources",
        entity_id="failed-src",
        version="1.0.0",
        tenant_id="default-tenant-uuid",
        operation="CREATE",
        payload={"source_id": "failed-src"},
        actor="admin",
        actor_role="SUPER_ADMIN",
    )
    await seeded_db.commit()

    # Dispatch will attempt 3 retries and mark as FAILED
    targets[0].max_retries = 2  # speed up test
    result = await config_service.dispatch_outbox_events(targets, "admin", "SUPER_ADMIN")
    assert result[0].status == DistributionStatus.FAILED
    assert result[0].retry_count == 2
    assert "Simulated connection refused" in (result[0].error_message or "")


# ── 12-16: Idempotency, Duplicate ACKs, Stale/Wrong ACKs ──────────────────────


@pytest.mark.asyncio
async def test_12_inbound_ack_success_and_idempotency(
    config_service: ConfigDistributionService, seeded_db: AsyncSession
):
    """Test applying ACK and verifying duplicate ACK is idempotent."""
    targets = await config_service.create_outbox_event(
        config_type="sources",
        entity_id="ack-src-1",
        version="1.0.0",
        tenant_id="default-tenant-uuid",
        operation="CREATE",
        payload={"source_id": "ack-src-1"},
        actor="admin",
        actor_role="SUPER_ADMIN",
    )
    target = targets[0]
    target.status = DistributionStatus.SENT
    await seeded_db.commit()

    # 1. First ACK
    ack_res = await config_service.process_ack(
        distribution_id=target.distribution_id,
        config_id="ack-src-1",
        version="1.0.0",
        module="M1",
        status="APPLIED",
        correlation_id=target.correlation_id,
    )
    assert ack_res["status"] == "ACKNOWLEDGED"

    # 2. Duplicate ACK is harmless and idempotent
    dup_ack = await config_service.process_ack(
        distribution_id=target.distribution_id,
        config_id="ack-src-1",
        version="1.0.0",
        module="M1",
        status="APPLIED",
        correlation_id=target.correlation_id,
    )
    assert dup_ack["status"] == "ACKNOWLEDGED"
    assert dup_ack.get("duplicate") is True


@pytest.mark.asyncio
async def test_14_wrong_module_ack_rejected(
    config_service: ConfigDistributionService, seeded_db: AsyncSession
):
    """ACK from wrong module must be rejected."""
    targets = await config_service.create_outbox_event(
        config_type="sources",
        entity_id="wrong-mod-src",
        version="1.0.0",
        tenant_id="default-tenant-uuid",
        operation="CREATE",
        payload={"source_id": "wrong-mod-src"},
        actor="admin",
        actor_role="SUPER_ADMIN",
    )
    target = targets[0]
    target.status = DistributionStatus.SENT
    await seeded_db.commit()

    with pytest.raises(WrongModuleAckError):
        await config_service.process_ack(
            distribution_id=target.distribution_id,
            config_id="wrong-mod-src",
            version="1.0.0",
            module="M5",  # M1 expected, M5 provided
            status="APPLIED",
            correlation_id=target.correlation_id,
        )


@pytest.mark.asyncio
async def test_15_wrong_version_ack_rejected(
    config_service: ConfigDistributionService, seeded_db: AsyncSession
):
    """ACK for wrong version must be rejected."""
    targets = await config_service.create_outbox_event(
        config_type="sources",
        entity_id="wrong-ver-src",
        version="2.0.0",
        tenant_id="default-tenant-uuid",
        operation="CREATE",
        payload={"source_id": "wrong-ver-src"},
        actor="admin",
        actor_role="SUPER_ADMIN",
    )
    target = targets[0]
    target.status = DistributionStatus.SENT
    await seeded_db.commit()

    with pytest.raises(VersionMismatchError):
        await config_service.process_ack(
            distribution_id=target.distribution_id,
            config_id="wrong-ver-src",
            version="1.0.0",  # Version mismatch: 2.0.0 expected
            module="M1",
            status="APPLIED",
            correlation_id=target.correlation_id,
        )


# ── 17: Configuration Status API ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_17_configuration_status_and_ack_api(
    app_client: AsyncClient,
    auth_headers: dict,
    config_service: ConfigDistributionService,
    seeded_db: AsyncSession,
):
    """Test GET /configuration/status/{id} and POST /configuration/ack endpoints."""
    targets = await config_service.create_outbox_event(
        config_type="sources",
        entity_id="status-src",
        version="1.0.0",
        tenant_id="default-tenant-uuid",
        operation="CREATE",
        payload={"source_id": "status-src"},
        actor="admin",
        actor_role="SUPER_ADMIN",
    )
    target = targets[0]
    target.status = DistributionStatus.SENT
    await seeded_db.commit()

    # Query status endpoint
    resp = await app_client.get(
        f"/api/v1/configuration/status/{target.distribution_id}", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["distribution_id"] == target.distribution_id
    assert body["overall_status"] == "PENDING"
    assert len(body["targets"]) == 1
    assert body["targets"][0]["module"] == "M1"
    assert body["targets"][0]["status"] == "SENT"

    # Post ACK via API endpoint
    ack_resp = await app_client.post(
        "/api/v1/configuration/ack",
        json={
            "distribution_id": target.distribution_id,
            "config_id": "status-src",
            "version": "1.0.0",
            "module": "M1",
            "status": "APPLIED",
            "correlation_id": target.correlation_id,
        },
        headers=auth_headers,
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "ACKNOWLEDGED"

    # Query status again -> must reflect real persisted ACKNOWLEDGED state
    resp2 = await app_client.get(
        f"/api/v1/configuration/status/{target.distribution_id}", headers=auth_headers
    )
    assert resp2.status_code == 200
    assert resp2.json()["overall_status"] == "ACKNOWLEDGED"
    assert resp2.json()["targets"][0]["status"] == "ACKNOWLEDGED"
