"""Replay service — manages replay lifecycle and Kafka publication."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.audit.audit_service import AuditService
from backend.app.core.logging import get_logger
from backend.app.models.audit_log import AuditAction
from backend.app.models.replay import ReplayOperation, ReplayStatus
from backend.app.repositories.replay_repo import ReplayRepository

logger = get_logger("replay_service")


class ReplayService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = ReplayRepository(db)
        self._audit = AuditService(db)

    async def request_replay(
        self,
        *,
        event_id: str,
        source: str | None,
        reason: str | None,
        requested_by: str,
        actor_role: str | None,
    ) -> ReplayOperation:
        op = ReplayOperation(
            event_id=event_id,
            source=source,
            reason=reason,
            requested_by=requested_by,
            status=ReplayStatus.REQUESTED,
        )
        op = await self._repo.create(op)

        # Publish to Kafka replay topic (best-effort)
        await self._publish_replay_request(op)

        await self._audit.record(
            actor=requested_by,
            actor_role=actor_role,
            action=AuditAction.REPLAY_REQUESTED,
            resource_type="replay",
            resource_id=event_id,
            after_state={
                "replay_id": op.id,
                "event_id": event_id,
                "source": source,
                "reason": reason,
            },
        )
        return op

    async def _publish_replay_request(self, op: ReplayOperation) -> None:
        from datetime import UTC, datetime

        from backend.app.core.config import get_settings
        from backend.app.integrations.kafka_client import get_kafka_producer

        settings = get_settings()
        if not settings.enable_replay:
            return

        try:
            producer = await get_kafka_producer()
            if producer is None:
                logger.warning(
                    "Kafka unavailable — replay request not published", event_id=op.event_id
                )
                op.status = ReplayStatus.QUEUED
                return

            message = {
                "replay_id": op.id,
                "event_id": op.event_id,
                "source": op.source,
                "reason": op.reason,
                "requested_by": op.requested_by,
                "requested_at": op.requested_at.isoformat(),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            await producer.publish(settings.kafka_replay_topic, message)
            op.status = ReplayStatus.QUEUED
            logger.info("Replay request published to Kafka", event_id=op.event_id, replay_id=op.id)
        except Exception as exc:
            logger.error("Failed to publish replay to Kafka", error=str(exc), event_id=op.event_id)
            # Status stays REQUESTED — not failed, because the request was recorded
