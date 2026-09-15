"""Replay operation repository."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.replay import ReplayOperation, ReplayStatus
from backend.app.repositories.base import BaseRepository


class ReplayRepository(BaseRepository[ReplayOperation]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(ReplayOperation, db)

    async def search(
        self,
        *,
        status: ReplayStatus | None = None,
        requested_by: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[ReplayOperation], int]:
        stmt = select(ReplayOperation)
        filters = []
        if status:
            filters.append(ReplayOperation.status == status)
        if requested_by:
            filters.append(ReplayOperation.requested_by == requested_by)
        if filters:
            stmt = stmt.where(*filters)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = (await self._db.execute(count_stmt)).scalar_one()
        stmt = stmt.offset(skip).limit(limit).order_by(ReplayOperation.requested_at.desc())
        items = (await self._db.execute(stmt)).scalars().all()
        return items, total
