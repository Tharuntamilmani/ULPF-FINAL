"""Mapping repository."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.mapping import Mapping, MappingVersion
from backend.app.repositories.base import BaseRepository


class MappingRepository(BaseRepository[Mapping]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Mapping, db)

    async def resolve_mapping(
        self, mapping_id: str, tenant_id: str | None = None
    ) -> Mapping | None:
        """
        Deterministic mapping resolution:
        1. Active tenant-specific extension
        2. Otherwise active platform baseline (tenant_id IS NULL)
        3. Otherwise None
        """
        if tenant_id:
            stmt = (
                select(Mapping)
                .options(selectinload(Mapping.versions))
                .where(
                    Mapping.mapping_id == mapping_id,
                    Mapping.tenant_id == tenant_id,
                    Mapping.is_active.is_(True),
                )
            )
            res = (await self._db.execute(stmt)).scalar_one_or_none()
            if res:
                return res

        # Fallback to active platform baseline
        stmt = (
            select(Mapping)
            .options(selectinload(Mapping.versions))
            .where(
                Mapping.mapping_id == mapping_id,
                Mapping.tenant_id.is_(None),
                Mapping.is_active.is_(True),
            )
        )
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def get_by_id_scoped(self, id: str, tenant_id: str | None = None) -> Mapping | None:
        """Get mapping by DB primary key, accessible if owned by tenant or platform baseline."""
        stmt = select(Mapping).options(selectinload(Mapping.versions)).where(Mapping.id == id)
        if tenant_id:
            stmt = stmt.where(or_(Mapping.tenant_id == tenant_id, Mapping.tenant_id.is_(None)))
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def get_by_mapping_id(
        self, mapping_id: str, tenant_id: str | None = None
    ) -> Mapping | None:
        stmt = (
            select(Mapping)
            .options(selectinload(Mapping.versions))
            .where(Mapping.mapping_id == mapping_id)
        )
        if tenant_id is not None:
            stmt = stmt.where(Mapping.tenant_id == tenant_id)
        else:
            stmt = stmt.where(Mapping.tenant_id.is_(None))
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def search(
        self,
        *,
        q: str | None = None,
        source_format: str | None = None,
        target_schema: str | None = None,
        tenant_id: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[Mapping], int]:
        stmt = select(Mapping)
        filters = []
        if tenant_id:
            filters.append(or_(Mapping.tenant_id == tenant_id, Mapping.tenant_id.is_(None)))
        if q:
            filters.append(
                or_(
                    Mapping.name.ilike(f"%{q}%"),
                    Mapping.mapping_id.ilike(f"%{q}%"),
                )
            )
        if source_format:
            filters.append(Mapping.source_format == source_format)
        if target_schema:
            filters.append(Mapping.target_schema == target_schema)
        if filters:
            stmt = stmt.where(*filters)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = (await self._db.execute(count_stmt)).scalar_one()
        stmt = stmt.offset(skip).limit(limit).order_by(Mapping.created_at.desc())
        items = (await self._db.execute(stmt)).scalars().all()
        return items, total

    async def add_version(
        self, mapping: Mapping, changed_by: str | None, reason: str | None
    ) -> MappingVersion:
        mv = MappingVersion(
            mapping_id=mapping.id,
            version=mapping.version,
            fields_snapshot=dict(mapping.fields),
            changed_by=changed_by,
            reason=reason,
        )
        self._db.add(mv)
        await self._db.flush()
        return mv

    async def mapping_id_exists(self, mapping_id: str, tenant_id: str | None = None) -> bool:
        stmt = select(func.count()).where(Mapping.mapping_id == mapping_id)
        if tenant_id is not None:
            stmt = stmt.where(Mapping.tenant_id == tenant_id)
        else:
            stmt = stmt.where(Mapping.tenant_id.is_(None))
        return (await self._db.execute(stmt)).scalar_one() > 0
