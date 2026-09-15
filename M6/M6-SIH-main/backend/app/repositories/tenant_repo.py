"""Tenant repository."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import Tenant, TenantStatus
from backend.app.repositories.base import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Tenant, db)

    async def get_by_slug(self, slug: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.slug == slug)
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        stmt = select(func.count()).where(Tenant.slug == slug)
        return (await self._db.execute(stmt)).scalar_one() > 0

    async def list_tenants(
        self,
        *,
        status: TenantStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[Tenant], int]:
        stmt = select(Tenant)
        if status:
            stmt = stmt.where(Tenant.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = (await self._db.execute(count_stmt)).scalar_one()
        stmt = stmt.offset(skip).limit(limit).order_by(Tenant.created_at.desc())
        items = (await self._db.execute(stmt)).scalars().all()
        return items, total
