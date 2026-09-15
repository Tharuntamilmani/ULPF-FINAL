import hashlib
import json
from typing import Any

import structlog
from aiokafka import AIOKafkaProducer

from app.envelope.models import RawEventEnvelope

logger = structlog.get_logger(__name__)

TOPIC_RAW = "ulpf.raw"
TOPIC_DLQ = "ulpf.dlq"
TOPIC_REPLAY = "ulpf.replay"


class KafkaProducerWrapper:
    def __init__(
        self,
        bootstrap_servers: str,
        raw_topic: str = TOPIC_RAW,
        acks: str = "all",
        enable_idempotence: bool = True,
        compression_type: str | None = "gzip",
    ):
        self.bootstrap_servers = bootstrap_servers
        self.raw_topic = raw_topic
        self.acks = acks
        self.enable_idempotence = enable_idempotence
        self.compression_type = compression_type
        self.producer: AIOKafkaProducer | None = None
        self._running = False

    async def start(self) -> None:
        if self.producer is None:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k if isinstance(k, bytes) else str(k).encode("utf-8"),
                acks=self.acks,
                enable_idempotence=self.enable_idempotence,
                compression_type=self.compression_type,
                request_timeout_ms=10000,
                retry_backoff_ms=200,
            )
        try:
            await self.producer.start()
            self._running = True
            logger.info("Kafka producer started", servers=self.bootstrap_servers, acks=self.acks)
        except Exception as e:
            logger.error("Failed to start Kafka producer", error=str(e))
            self._running = False
            raise

    async def stop(self) -> None:
        if self.producer and self._running:
            try:
                await self.producer.stop()
                logger.info("Kafka producer stopped")
            finally:
                self._running = False

    @staticmethod
    def compute_partition_key(tenant_id: str, source_id: str) -> bytes:
        """
        Partition key = sha256(tenant_id + source_id) for predictable source affinity.
        """
        combined = f"{tenant_id}:{source_id}".encode()
        return hashlib.sha256(combined).hexdigest().encode("utf-8")

    async def publish_envelope(
        self, envelope: RawEventEnvelope, topic: str | None = None
    ) -> dict[str, Any]:
        if not self.producer or not self._running:
            raise RuntimeError("Kafka producer is not running")

        target_topic = topic or self.raw_topic
        key = self.compute_partition_key(envelope.tenant_id, envelope.source_id)
        envelope_dict = envelope.model_dump()

        headers = [
            ("raw_event_id", envelope.raw_event_id.encode("utf-8")),
            ("tenant_id", envelope.tenant_id.encode("utf-8")),
            ("source_id", envelope.source_id.encode("utf-8")),
            ("received_at", envelope.received_at.encode("utf-8")),
            ("schema_version", envelope.schema_version.encode("utf-8")),
        ]

        record_metadata = await self.producer.send_and_wait(
            target_topic,
            value=envelope_dict,
            key=key,
            headers=headers,
        )
        return {
            "topic": record_metadata.topic,
            "partition": record_metadata.partition,
            "offset": record_metadata.offset,
            "timestamp": record_metadata.timestamp,
        }

    async def is_healthy(self) -> bool:
        if not self.producer or not self._running:
            try:
                await self.start()
            except Exception:
                return False
        return self._running
