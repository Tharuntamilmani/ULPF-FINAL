import argparse
import asyncio
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, File, Header, Request, UploadFile
from pydantic import BaseModel

from app.config.settings import Settings, get_settings
from app.envelope.models import RawEventEnvelope
from app.messaging.kafka import KafkaProducerWrapper
from app.storage.outbox import DurableOutbox
from app.storage.raw_vault import RawVault
from app.transports.http import verify_bearer_token
from app.transports.pipeline import process_raw_payload

logger = structlog.get_logger(__name__)

router = APIRouter()


class FileReplayResponse(BaseModel):
    status: str = "completed"
    total_events: int
    raw_event_ids: list[str]


async def replay_file(
    file_path: Path,
    settings: Settings,
    raw_vault: RawVault,
    kafka_producer: KafkaProducerWrapper,
    tenant_id: str | None = None,
    source_id: str | None = None,
    source_type: str | None = None,
    outbox: DurableOutbox | None = None,
) -> list[RawEventEnvelope]:
    """
    Replays a log file line-by-line through the M1 ingestion boundary pipeline.
    Preserves exact line bytes (including line terminators).
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Replay file not found: {file_path}")

    metadata: dict[str, Any] = {
        "tenant_id": tenant_id or settings.default_tenant_id,
        "source_id": source_id or f"file-replay-{file_path.stem}",
        "source_type": source_type or settings.default_source_type,
        "ingest_zone": settings.default_ingest_zone,
        "collector_id": settings.default_collector_id,
    }

    envelopes: list[RawEventEnvelope] = []
    with open(file_path, "rb") as f:
        for line in f:
            if not line:
                continue

            envelope = await process_raw_payload(
                raw_bytes=line,
                metadata=metadata,
                transport_protocol="file_replay",
                transport_port=None,
                raw_vault=raw_vault,
                kafka_producer=kafka_producer,
                format_hint="syslog",
                bucket_name=settings.minio_bucket_raw,
                outbox=outbox,
            )
            envelopes.append(envelope)

    logger.info(
        "File replay completed",
        file=str(file_path),
        total_events=len(envelopes),
    )
    return envelopes


async def handle_file_replay_endpoint(
    request: Request,
    file: UploadFile = File(...),
    authorization: str | None = Header(None, alias="Authorization"),
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    x_source_id: str | None = Header(None, alias="X-Source-ID"),
) -> FileReplayResponse:
    settings: Settings = request.app.state.settings
    verify_bearer_token(authorization=authorization, settings=settings)

    raw_vault: RawVault = request.app.state.raw_vault
    kafka_producer: KafkaProducerWrapper = request.app.state.kafka_producer
    outbox: DurableOutbox | None = getattr(request.app.state, "outbox", None)

    content = await file.read()
    lines = content.splitlines(keepends=True)

    metadata: dict[str, Any] = {
        "tenant_id": x_tenant_id or settings.default_tenant_id,
        "source_id": x_source_id or f"file-upload-{file.filename}",
        "source_type": settings.default_source_type,
        "ingest_zone": settings.default_ingest_zone,
        "collector_id": settings.default_collector_id,
    }

    event_ids: list[str] = []
    for line in lines:
        if not line:
            continue

        envelope = await process_raw_payload(
            raw_bytes=line,
            metadata=metadata,
            transport_protocol="file_replay",
            transport_port=None,
            raw_vault=raw_vault,
            kafka_producer=kafka_producer,
            format_hint="syslog",
            bucket_name=settings.minio_bucket_raw,
            outbox=outbox,
        )
        event_ids.append(envelope.raw_event_id)

    return FileReplayResponse(
        status="completed",
        total_events=len(event_ids),
        raw_event_ids=event_ids,
    )


async def main_cli() -> None:
    parser = argparse.ArgumentParser(description="ULPF M1 Ingestion File Replay CLI")
    parser.add_argument("file", type=str, help="Path to log file to replay")
    parser.add_argument("--tenant", type=str, help="Tenant ID")
    parser.add_argument("--source", type=str, help="Source ID")
    args = parser.parse_args()

    settings = get_settings()

    raw_vault = RawVault(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
        default_bucket=settings.minio_bucket_raw,
    )
    await raw_vault.ensure_bucket()

    kafka_producer = KafkaProducerWrapper(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        raw_topic=settings.kafka_topic_raw,
    )
    await kafka_producer.start()

    try:
        file_path = Path(args.file)
        envelopes = await replay_file(
            file_path=file_path,
            settings=settings,
            raw_vault=raw_vault,
            kafka_producer=kafka_producer,
            tenant_id=args.tenant,
            source_id=args.source,
        )
        print(f"✅ Replayed {len(envelopes)} events from {file_path}")
        for env in envelopes[:5]:
            print(f"  - Event ID: {env.raw_event_id} | SHA-256: {env.integrity.hash[:16]}...")
    finally:
        await kafka_producer.stop()


if __name__ == "__main__":
    asyncio.run(main_cli())
