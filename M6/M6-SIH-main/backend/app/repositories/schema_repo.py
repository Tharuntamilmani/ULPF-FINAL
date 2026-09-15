"""Schema repository."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.schema import Schema, SchemaStatus, SchemaVersion
from backend.app.repositories.base import BaseRepository


class SchemaRepository(BaseRepository[Schema]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Schema, db)

    async def get_by_name(self, name: str) -> Schema | None:
        stmt = select(Schema).options(selectinload(Schema.versions)).where(Schema.name == name)
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def get_version(self, schema_name: str, version: str) -> SchemaVersion | None:
        stmt = (
            select(SchemaVersion)
            .join(Schema, Schema.id == SchemaVersion.schema_id)
            .where(Schema.name == schema_name, SchemaVersion.version == version)
        )
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def list_schemas(
        self, *, skip: int = 0, limit: int = 100
    ) -> tuple[Sequence[Schema], int]:
        count_stmt = select(func.count()).select_from(Schema)
        total: int = (await self._db.execute(count_stmt)).scalar_one()
        stmt = (
            select(Schema)
            .options(selectinload(Schema.versions))
            .offset(skip)
            .limit(limit)
            .order_by(Schema.name)
        )
        items = (await self._db.execute(stmt)).scalars().all()
        return items, total

    async def add_version(
        self,
        schema: Schema,
        version: str,
        json_schema: dict[str, Any],
        changelog: str | None,
        created_by: str | None,
    ) -> SchemaVersion:
        sv = SchemaVersion(
            schema_id=schema.id,
            version=version,
            json_schema=json_schema,
            changelog=changelog,
            created_by=created_by,
            status=SchemaStatus.ACTIVE,
        )
        self._db.add(sv)
        await self._db.flush()
        return sv

    async def name_exists(self, name: str) -> bool:
        stmt = select(func.count()).where(Schema.name == name)
        return (await self._db.execute(stmt)).scalar_one() > 0
