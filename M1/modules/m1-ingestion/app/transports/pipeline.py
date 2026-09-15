import time
from typing import Any

import structlog

from app.envelope.builder import build_envelope
from app.envelope.models import RawEventEnvelope
from app.health.metrics import (
    INGEST_BYTES_TOTAL,
    INGEST_EVENTS_TOTAL,
    INGEST_LATENCY_SECONDS,
    KAFKA_PUBLISH_ERRORS_TOTAL,
    KAFKA_PUBLISH_TOTAL,
    RAW_VAULT_WRITE_TOTAL,
)
from app.messaging.kafka import KafkaProducerWrapper
from app.storage.raw_vault import RawVault

logger = structlog.get_logger(__name__)


class MinIOWriteError(Exception):
    """Raised when writing the raw payload to MinIO vault fails."""


class KafkaPublishError(Exception):
    """Raised when Kafka publication fails, but raw payload is already persisted in MinIO vault."""

    def __init__(self, message: str, envelope: RawEventEnvelope):
        super().__init__(message)
        self.envelope = envelope


async def process_raw_payload(
    raw_bytes: bytes,
    metadata: dict[str, Any],
    transport_protocol: str,
    transport_port: int | None,
    raw_vault: RawVault,
    kafka_producer: KafkaProducerWrapper,
    format_hint: str = "syslog",
    bucket_name: str = "ulpf-raw",
    outbox: Any | None = None,
) -> RawEventEnvelope:
    """
    Core M1 ingestion boundary pipeline:
    Receive bytes -> Generate UUIDv7 & SHA-256 -> Build Envelope -> Store in MinIO -> Publish to Kafka.
    If Kafka publish fails, the envelope is durably spooled into the local Outbox so raw evidence
    is never orphaned and is eventually replayed.
    """
    start_time = time.perf_counter()
    transport_name = transport_protocol.lower()

    INGEST_BYTES_TOTAL.labels(transport=transport_name).inc(len(raw_bytes))

    # 1. Build Envelope (calculates SHA256 over exact raw bytes & assigns UUIDv7)
    envelope = build_envelope(
        raw_bytes=raw_bytes,
        metadata=metadata,
        transport_protocol=transport_protocol,
        transport_port=transport_port,
        format_hint=format_hint,
        bucket_name=bucket_name,
    )

    # 2. Store untouched raw payload compressed in MinIO
    try:
        await raw_vault.store_raw_event(
            bucket=envelope.raw_storage.bucket,
            object_key=envelope.raw_storage.object_key,
            payload_bytes=raw_bytes,
        )
        RAW_VAULT_WRITE_TOTAL.labels(status="success").inc()
    except Exception as e:
        RAW_VAULT_WRITE_TOTAL.labels(status="error").inc()
        logger.error(
            "Failed to store raw payload in MinIO",
            raw_event_id=envelope.raw_event_id,
            error=str(e),
        )
        raise MinIOWriteError(f"Failed to store raw payload in MinIO: {e}") from e

    # 3. Publish RawEventEnvelope downstream to Kafka
    try:
        await kafka_producer.publish_envelope(envelope)
        KAFKA_PUBLISH_TOTAL.labels(topic=kafka_producer.raw_topic).inc()
    except Exception as e:
        KAFKA_PUBLISH_ERRORS_TOTAL.labels(topic=kafka_producer.raw_topic).inc()
        logger.error(
            "Failed to publish envelope to Kafka; spooling to durable outbox",
            raw_event_id=envelope.raw_event_id,
            error=str(e),
        )
        if outbox is not None:
            try:
                await outbox.spool_envelope(
                    envelope=envelope,
                    topic=kafka_producer.raw_topic,
                    error=str(e),
                )
            except Exception as outbox_err:
                logger.error(
                    "Critical: Failed to spool envelope to outbox",
                    raw_event_id=envelope.raw_event_id,
                    error=str(outbox_err),
                )
        raise KafkaPublishError(f"Kafka publish failed: {e}", envelope=envelope) from e

    duration = time.perf_counter() - start_time
    INGEST_LATENCY_SECONDS.labels(transport=transport_name).observe(duration)
    INGEST_EVENTS_TOTAL.labels(
        transport=transport_name, status="success", tenant_id=envelope.tenant_id
    ).inc()

    logger.info(
        "Raw event ingested and preserved",
        raw_event_id=envelope.raw_event_id,
        tenant_id=envelope.tenant_id,
        source_id=envelope.source_id,
        transport=transport_name,
        sha256=envelope.integrity.hash,
        object_key=envelope.raw_storage.object_key,
    )

    return envelope
