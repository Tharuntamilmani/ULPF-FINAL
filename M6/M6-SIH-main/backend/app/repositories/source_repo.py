"""Source repository with strict tenant isolation."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.source import Source, SourceStatus
from backend.app.repositories.base import BaseRepository


class SourceRepository(BaseRepository[Source]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Source, db)

    async def get_by_id_and_tenant(self, id: str, tenant_id: str | None) -> Source | None:
        stmt = select(Source).where(Source.id == id)
        if tenant_id is not None:
            stmt = stmt.where(Source.tenant_id == tenant_id)
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def get_by_source_id(self, source_id: str, tenant_id: str | None = None) -> Source | None:
        stmt = select(Source).where(Source.source_id == source_id)
        if tenant_id is not None:
            stmt = stmt.where(Source.tenant_id == tenant_id)
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def search(
        self,
        *,
        q: str | None = None,
        vendor: str | None = None,
        status: SourceStatus | None = None,
        tenant_id: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[Source], int]:
        stmt = select(Source)
        filters = []
        if q:
            filters.append(
                or_(
                    Source.name.ilike(f"%{q}%"),
                    Source.source_id.ilike(f"%{q}%"),
                    Source.vendor.ilike(f"%{q}%"),
                )
            )
        if vendor:
            filters.append(Source.vendor.ilike(f"%{vendor}%"))
        if status:
            filters.append(Source.status == status)
        if tenant_id:
            filters.append(Source.tenant_id == tenant_id)
        if filters:
            stmt = stmt.where(*filters)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = (await self._db.execute(count_stmt)).scalar_one()
        stmt = stmt.offset(skip).limit(limit).order_by(Source.created_at.desc())
        items = (await self._db.execute(stmt)).scalars().all()
        return items, total

    async def source_id_exists(self, source_id: str, tenant_id: str) -> bool:
        stmt = select(func.count()).where(
            Source.source_id == source_id,
            Source.tenant_id == tenant_id,
        )
        return (await self._db.execute(stmt)).scalar_one() > 0
