"""Unit tests for Policy registry."""

from __future__ import annotations

import pytest

from backend.app.core.exceptions import DuplicateError, PolicyNotFound
from backend.app.registry.policy_registry import PolicyRegistry
from backend.app.schemas.policy import PolicyCondition, PolicyCreate, PolicyUpdate


def _make_policy(**overrides) -> PolicyCreate:
    defaults = dict(
        policy_id="test-policy-01",
        name="Test Policy",
        version="1.0.0",
        priority=50,
        conditions=[PolicyCondition(field="event.severity.value", operator=">=", value=5)],
        destinations=["siem"],
        is_enabled=True,
    )
    defaults.update(overrides)
    return PolicyCreate(**defaults)


@pytest.mark.asyncio
async def test_create_policy(db_session):
    registry = PolicyRegistry(db_session)
    policy = await registry.create(_make_policy(), "admin", "ADMINISTRATOR")
    assert policy.policy_id == "test-policy-01"
    assert policy.is_enabled is True
    assert len(policy.conditions) == 1


@pytest.mark.asyncio
async def test_duplicate_policy_raises(db_session):
    registry = PolicyRegistry(db_session)
    await registry.create(_make_policy(), "admin", "ADMINISTRATOR")
    with pytest.raises(DuplicateError):
        await registry.create(_make_policy(), "admin", "ADMINISTRATOR")


@pytest.mark.asyncio
async def test_policy_not_found(db_session):
    registry = PolicyRegistry(db_session)
    with pytest.raises(PolicyNotFound):
        await registry.get("nonexistent-uuid")


@pytest.mark.asyncio
async def test_enable_disable_policy(db_session):
    registry = PolicyRegistry(db_session)
    policy = await registry.create(_make_policy(is_enabled=True), "admin", "ADMINISTRATOR")

    disabled = await registry.disable(policy.id, "admin", "ADMINISTRATOR")
    assert disabled.is_enabled is False

    enabled = await registry.enable(policy.id, "admin", "ADMINISTRATOR")
    assert enabled.is_enabled is True


@pytest.mark.asyncio
async def test_update_policy_creates_version(db_session):
    registry = PolicyRegistry(db_session)
    policy = await registry.create(_make_policy(), "admin", "ADMINISTRATOR")
    updated = await registry.update(
        policy.id,
        PolicyUpdate(name="Updated Policy", reason="SIH demo update"),
        "admin",
        "ADMINISTRATOR",
    )
    assert updated.name == "Updated Policy"
