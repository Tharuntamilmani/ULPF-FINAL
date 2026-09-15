"""Unit tests for Mapping registry."""

from __future__ import annotations

import pytest

from backend.app.core.exceptions import DuplicateError, MappingNotFound
from backend.app.registry.mapping_registry import MappingRegistry
from backend.app.schemas.mapping import MappingCreate, MappingUpdate


def _make_mapping(**overrides) -> MappingCreate:
    defaults = dict(
        mapping_id="cisco-asa-ues-v1-test",
        name="Cisco ASA → UES v1",
        source_format="cisco-asa",
        target_schema="ues",
        target_version="1.0.0",
        fields={"srcip": "source.ip", "dstip": "destination.ip", "action": "event.action"},
    )
    defaults.update(overrides)
    return MappingCreate(**defaults)


@pytest.mark.asyncio
async def test_create_mapping(db_session):
    registry = MappingRegistry(db_session)
    mapping = await registry.create(_make_mapping(), "admin", "ADMINISTRATOR")
    assert mapping.mapping_id == "cisco-asa-ues-v1-test"
    assert mapping.fields["srcip"] == "source.ip"


@pytest.mark.asyncio
async def test_duplicate_mapping_raises(db_session):
    registry = MappingRegistry(db_session)
    await registry.create(_make_mapping(), "admin", "ADMINISTRATOR")
    with pytest.raises(DuplicateError):
        await registry.create(_make_mapping(), "admin", "ADMINISTRATOR")


@pytest.mark.asyncio
async def test_update_mapping(db_session):
    registry = MappingRegistry(db_session)
    mapping = await registry.create(_make_mapping(), "admin", "ADMINISTRATOR")
    updated = await registry.update(
        mapping.id,
        MappingUpdate(fields={"srcip": "source.ip", "dstip": "destination.ip"}),
        "admin",
        "ADMINISTRATOR",
    )
    assert "action" not in updated.fields


@pytest.mark.asyncio
async def test_mapping_not_found(db_session):
    registry = MappingRegistry(db_session)
    with pytest.raises(MappingNotFound):
        await registry.get("nonexistent-uuid")
