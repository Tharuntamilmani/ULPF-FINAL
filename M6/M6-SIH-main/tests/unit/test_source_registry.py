"""Unit tests for Source Registry."""

from __future__ import annotations

import pytest

from backend.app.core.exceptions import DuplicateError, SourceNotFound
from backend.app.models.source import SourceStatus
from backend.app.registry.source_registry import SourceRegistry
from backend.app.schemas.source import SourceCreate, SourceUpdate


def _make_source(**overrides) -> SourceCreate:
    defaults = {
        "source_id": "test-src-01",
        "name": "Test Source",
        "vendor": "TestVendor",
        "product": "TestProduct",
        "source_type": "firewall",
        "protocol": "syslog",
        "transport": "udp",
        "port": 514,
    }
    defaults.update(overrides)
    return SourceCreate(**defaults)


@pytest.mark.asyncio
async def test_create_source(db_session):
    registry = SourceRegistry(db_session)
    source = await registry.create(_make_source(), "admin", "ADMINISTRATOR")
    assert source.source_id == "test-src-01"
    assert source.status == SourceStatus.ACTIVE


@pytest.mark.asyncio
async def test_duplicate_source_id_raises(db_session):
    registry = SourceRegistry(db_session)
    await registry.create(_make_source(), "admin", "ADMINISTRATOR")
    with pytest.raises(DuplicateError):
        await registry.create(_make_source(), "admin", "ADMINISTRATOR")


@pytest.mark.asyncio
async def test_get_source_not_found(db_session):
    registry = SourceRegistry(db_session)
    with pytest.raises(SourceNotFound):
        await registry.get("nonexistent-uuid")


@pytest.mark.asyncio
async def test_update_source(db_session):
    registry = SourceRegistry(db_session)
    source = await registry.create(_make_source(), "admin", "ADMINISTRATOR")
    updated = await registry.update(
        source.id, SourceUpdate(name="Updated Name"), "admin", "ADMINISTRATOR"
    )
    assert updated.name == "Updated Name"


@pytest.mark.asyncio
async def test_disable_and_enable_source(db_session):
    registry = SourceRegistry(db_session)
    source = await registry.create(_make_source(), "admin", "ADMINISTRATOR")
    assert source.status == SourceStatus.ACTIVE

    disabled = await registry.disable(source.id, "admin", "ADMINISTRATOR")
    assert disabled.status == SourceStatus.DISABLED

    enabled = await registry.enable(source.id, "admin", "ADMINISTRATOR")
    assert enabled.status == SourceStatus.ACTIVE


@pytest.mark.asyncio
async def test_delete_source(db_session):
    registry = SourceRegistry(db_session)
    source = await registry.create(_make_source(), "admin", "ADMINISTRATOR")
    await registry.delete(source.id, "admin", "ADMINISTRATOR")
    with pytest.raises(SourceNotFound):
        await registry.get(source.id)


@pytest.mark.asyncio
async def test_list_sources_pagination(db_session):
    registry = SourceRegistry(db_session)
    for i in range(5):
        await registry.create(_make_source(source_id=f"src-{i}"), "admin", "ADMINISTRATOR")
    items, total = await registry.list(page=1, page_size=3)
    assert total == 5
    assert len(items) == 3
