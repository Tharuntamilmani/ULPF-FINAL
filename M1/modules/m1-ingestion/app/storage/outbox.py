import asyncio
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import structlog

from app.envelope.models import RawEventEnvelope

logger = structlog.get_logger(__name__)


class DurableOutbox:
    """
    SQLite-backed durable outbox spool for envelopes that failed initial Kafka publish.
    Ensures that raw objects persisted to MinIO are never orphaned and are eventually replayed.
    """

    def __init__(self, db_path: str = "data/outbox.db"):
        self.db_path = db_path
        self._recovery_task: asyncio.Task[None] | None = None
        self._running = False
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS outbox_events (
                    raw_event_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    raw_object_key TEXT,
                    envelope_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_outbox_created_at ON outbox_events (created_at)"
            )
            conn.commit()

    async def init_db(self) -> None:
        await asyncio.to_thread(self._init_db)

    async def close(self) -> None:
        await self.stop_recovery_worker()

    def _spool_sync(
        self,
        envelope_dict: dict[str, Any],
        topic: str,
        error: str = "",
        raw_object_key: str | None = None,
    ) -> None:
        raw_event_id = envelope_dict["raw_event_id"]
        tenant_id = envelope_dict["tenant_id"]
        source_id = envelope_dict["source_id"]
        object_key = raw_object_key or envelope_dict.get("raw_storage", {}).get("object_key", "")
        envelope_json = json.dumps(envelope_dict)
        now = time.time()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO outbox_events
                (raw_event_id, tenant_id, source_id, topic, raw_object_key, envelope_json, created_at, attempts, last_error)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (raw_event_id, tenant_id, source_id, topic, object_key, envelope_json, now, error),
            )
            conn.commit()
        logger.warning(
            "Envelope spooled to durable outbox",
            raw_event_id=raw_event_id,
            tenant_id=tenant_id,
            topic=topic,
            error=error,
        )

    async def spool_envelope(
        self,
        envelope: RawEventEnvelope,
        topic: str,
        error: str = "",
        error_reason: str = "",
        raw_object_key: str | None = None,
    ) -> None:
        err_msg = error or error_reason
        envelope_dict = envelope.model_dump()
        obj_key = raw_object_key or envelope.raw_storage.object_key
        await asyncio.to_thread(self._spool_sync, envelope_dict, topic, err_msg, obj_key)

    def _get_pending_sync(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT raw_event_id, tenant_id, source_id, topic, raw_object_key, envelope_json, attempts, last_error
                FROM outbox_events
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["status"] = "pending"
                result.append(d)
            return result

    async def get_pending_records(self, limit: int = 100) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._get_pending_sync, limit)

    def _mark_published_sync(self, raw_event_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM outbox_events WHERE raw_event_id = ?", (raw_event_id,))
            conn.commit()

    async def mark_replayed(self, raw_event_id: str) -> None:
        await asyncio.to_thread(self._mark_published_sync, raw_event_id)

    def _record_attempt_sync(self, raw_event_id: str, error: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE outbox_events
                SET attempts = attempts + 1, last_error = ?
                WHERE raw_event_id = ?
                """,
                (error, raw_event_id),
            )
            conn.commit()

    def _get_pending_count_sync(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM outbox_events")
            res = cursor.fetchone()
            return int(res[0]) if res else 0

    async def get_pending_count(self) -> int:
        return await asyncio.to_thread(self._get_pending_count_sync)

    async def replay_pending(
        self,
        kafka_producer: Any,
        limit: int = 100,
        batch_size: int | None = None,
    ) -> int:
        """
        Attempts to replay spooled outbox events to Kafka.
        Returns the number of successfully published and removed events.
        """
        actual_limit = batch_size if batch_size is not None else limit
        pending = await asyncio.to_thread(self._get_pending_sync, actual_limit)
        if not pending:
            return 0

        success_count = 0
        for item in pending:
            raw_event_id = item["raw_event_id"]
            topic = item["topic"]
            try:
                envelope_dict = json.loads(item["envelope_json"])
                envelope = RawEventEnvelope.model_validate(envelope_dict)
                await kafka_producer.publish_envelope(envelope, topic=topic)
                await asyncio.to_thread(self._mark_published_sync, raw_event_id)
                success_count += 1
                logger.info(
                    "Outbox event successfully replayed to Kafka", raw_event_id=raw_event_id
                )
            except Exception as e:
                await asyncio.to_thread(self._record_attempt_sync, raw_event_id, str(e))
                logger.warning(
                    "Failed to replay outbox event to Kafka",
                    raw_event_id=raw_event_id,
                    error=str(e),
                )
                # Break early if Kafka is still unresponsive
                break

        return success_count

    async def _recovery_loop(self, kafka_producer: Any, interval: float = 5.0) -> None:
        while self._running:
            try:
                count = await self.get_pending_count()
                if count > 0:
                    is_healthy = await kafka_producer.is_healthy()
                    if is_healthy:
                        replayed = await self.replay_pending(kafka_producer)
                        if replayed > 0:
                            logger.info("Outbox batch replayed", count=replayed)
            except Exception as e:
                logger.debug("Outbox recovery check warning", error=str(e))
            await asyncio.sleep(interval)

    def start_recovery_worker(self, kafka_producer: Any, interval: float = 5.0) -> None:
        if not self._running:
            self._running = True
            self._recovery_task = asyncio.create_task(self._recovery_loop(kafka_producer, interval))
            logger.info("Durable outbox recovery worker started")

    async def stop_recovery_worker(self) -> None:
        self._running = False
        if self._recovery_task:
            self._recovery_task.cancel()
            try:
                await self._recovery_task
            except asyncio.CancelledError:
                pass
            self._recovery_task = None
            logger.info("Durable outbox recovery worker stopped")
