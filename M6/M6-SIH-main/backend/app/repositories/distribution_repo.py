"""Distribution target repository."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.config_distribution import DistributionStatus, DistributionTargetState
from backend.app.repositories.base import BaseRepository


class DistributionRepository(BaseRepository[DistributionTargetState]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(DistributionTargetState, db)

    async def get_by_distribution_and_module(
        self, distribution_id: str, module: str
    ) -> DistributionTargetState | None:
        stmt = select(DistributionTargetState).where(
            DistributionTargetState.distribution_id == distribution_id,
            DistributionTargetState.target_module == module,
        )
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def list_by_distribution_id(
        self, distribution_id: str
    ) -> Sequence[DistributionTargetState]:
        stmt = (
            select(DistributionTargetState)
            .where(DistributionTargetState.distribution_id == distribution_id)
            .order_by(DistributionTargetState.created_at.asc())
        )
        return (await self._db.execute(stmt)).scalars().all()

    async def list_by_config_version(
        self, config_version_id: str
    ) -> Sequence[DistributionTargetState]:
        stmt = (
            select(DistributionTargetState)
            .where(DistributionTargetState.config_version_id == config_version_id)
            .order_by(DistributionTargetState.created_at.asc())
        )
        return (await self._db.execute(stmt)).scalars().all()

    async def list_by_config_key(self, config_key: str) -> Sequence[DistributionTargetState]:
        stmt = (
            select(DistributionTargetState)
            .where(DistributionTargetState.config_type == config_key)
            .order_by(DistributionTargetState.created_at.desc())
        )
        return (await self._db.execute(stmt)).scalars().all()

    async def list_pending(self, limit: int = 50) -> Sequence[DistributionTargetState]:
        stmt = (
            select(DistributionTargetState)
            .where(DistributionTargetState.status == DistributionStatus.PENDING)
            .limit(limit)
        )
        return (await self._db.execute(stmt)).scalars().all()

    async def record_ack(
        self,
        distribution_id: str,
        module: str,
        version: str,
        status: DistributionStatus,
        error: str | None = None,
    ) -> DistributionTargetState | None:
        target = await self.get_by_distribution_and_module(distribution_id, module)
        if not target:
            return None

        # Stale ACK check: do not let an older version overwrite newer version
        if target.version != version:
            return None

        target.status = status
        target.ack_at = datetime.now(UTC)
        if error:
            target.error_message = error
        await self._db.flush()
        return target
