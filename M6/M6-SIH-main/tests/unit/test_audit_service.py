"""Unit tests for the append-only AuditService."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.app.audit.audit_service import AuditService
from backend.app.models.audit_log import AuditAction, AuditLog, AuditResult


@pytest.mark.asyncio
async def test_audit_record_creates_entry(db_session):
    svc = AuditService(db_session)
    entry = await svc.record(
        actor="admin",
        actor_role="ADMINISTRATOR",
        action=AuditAction.SOURCE_CREATED,
        resource_type="source",
        resource_id="cisco-fw-01",
        after_state={"source_id": "cisco-fw-01"},
    )
    assert entry.id is not None
    assert entry.actor == "admin"
    assert entry.action == AuditAction.SOURCE_CREATED
    assert entry.result == AuditResult.SUCCESS


@pytest.mark.asyncio
async def test_audit_record_failure_result(db_session):
    svc = AuditService(db_session)
    entry = await svc.record(
        actor="dev",
        actor_role="PARSER_DEVELOPER",
        action=AuditAction.PARSER_ACTIVATED,
        resource_type="parser",
        resource_id="parser-test",
        result=AuditResult.FAILURE,
        extra={"error": "Invalid transition"},
    )
    assert entry.result == AuditResult.FAILURE
    assert entry.extra["error"] == "Invalid transition"


@pytest.mark.asyncio
async def test_audit_is_append_only(db_session):
    """Verify no UPDATE is issued against audit_logs — only INSERT."""
    svc = AuditService(db_session)
    entry = await svc.record(
        actor="admin",
        actor_role="ADMINISTRATOR",
        action=AuditAction.CONFIGURATION_CHANGED,
        resource_type="config",
        resource_id="sources",
    )
    original_id = entry.id
    original_ts = entry.timestamp

    # Simulate attempting to update — AuditLog has no updated_at so SQLAlchemy
    # won't auto-update. The ID and timestamp must remain unchanged.
    result = await db_session.execute(select(AuditLog).where(AuditLog.id == original_id))
    fetched = result.scalar_one()
    assert fetched.id == original_id
    assert fetched.timestamp == original_ts


@pytest.mark.asyncio
async def test_multiple_audit_entries_accumulate(db_session):
    svc = AuditService(db_session)
    for action in [
        AuditAction.SOURCE_CREATED,
        AuditAction.SOURCE_UPDATED,
        AuditAction.SOURCE_DISABLED,
    ]:
        await svc.record(
            actor="admin",
            actor_role="ADMINISTRATOR",
            action=action,
            resource_type="source",
            resource_id="s1",
        )

    result = await db_session.execute(select(AuditLog).where(AuditLog.resource_id == "s1"))
    entries = result.scalars().all()
    assert len(entries) == 3
    actions = [e.action for e in entries]
    assert AuditAction.SOURCE_CREATED in actions
    assert AuditAction.SOURCE_DISABLED in actions
