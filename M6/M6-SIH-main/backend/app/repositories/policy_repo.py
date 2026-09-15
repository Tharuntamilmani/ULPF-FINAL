"""Policy repository with strict tenant isolation."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.policy import Policy, PolicyVersion
from backend.app.repositories.base import BaseRepository


class PolicyRepository(BaseRepository[Policy]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Policy, db)

    async def get_by_id_and_tenant(self, id: str, tenant_id: str | None) -> Policy | None:
        stmt = select(Policy).options(selectinload(Policy.versions)).where(Policy.id == id)
        if tenant_id is not None:
            stmt = stmt.where(Policy.tenant_id == tenant_id)
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def get_by_policy_id(self, policy_id: str, tenant_id: str | None = None) -> Policy | None:
        stmt = (
            select(Policy)
            .options(selectinload(Policy.versions))
            .where(Policy.policy_id == policy_id)
        )
        if tenant_id is not None:
            stmt = stmt.where(Policy.tenant_id == tenant_id)
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def search(
        self,
        *,
        q: str | None = None,
        is_enabled: bool | None = None,
        tenant_id: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[Policy], int]:
        stmt = select(Policy).options(selectinload(Policy.versions))
        filters = []
        if q:
            filters.append(
                or_(
                    Policy.name.ilike(f"%{q}%"),
                    Policy.policy_id.ilike(f"%{q}%"),
                )
            )
        if is_enabled is not None:
            filters.append(Policy.is_enabled == is_enabled)
        if tenant_id is not None:
            filters.append(Policy.tenant_id == tenant_id)
        if filters:
            stmt = stmt.where(*filters)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = (await self._db.execute(count_stmt)).scalar_one()
        stmt = (
            stmt.offset(skip)
            .limit(limit)
            .order_by(Policy.priority.desc(), Policy.created_at.desc())
        )
        items = (await self._db.execute(stmt)).scalars().all()
        return items, total

    async def add_version(
        self, policy: Policy, changed_by: str | None, reason: str | None
    ) -> PolicyVersion:
        pv = PolicyVersion(
            policy_id=policy.id,
            version=policy.version,
            conditions_snapshot=list(policy.conditions),
            destinations_snapshot=list(policy.destinations),
            changed_by=changed_by,
            reason=reason,
        )
        self._db.add(pv)
        await self._db.flush()
        return pv

    async def policy_id_exists(self, policy_id: str, tenant_id: str) -> bool:
        stmt = select(func.count()).where(
            Policy.policy_id == policy_id,
            Policy.tenant_id == tenant_id,
        )
        return (await self._db.execute(stmt)).scalar_one() > 0
