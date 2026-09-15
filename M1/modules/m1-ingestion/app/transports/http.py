from typing import Any

import structlog
from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel

from app.api.rate_limiter import TokenBucketRateLimiter
from app.config.settings import Settings, get_settings
from app.health.metrics import INGEST_REJECTED_TOTAL
from app.messaging.kafka import KafkaProducerWrapper
from app.storage.raw_vault import RawVault
from app.transports.pipeline import process_raw_payload

logger = structlog.get_logger(__name__)

router = APIRouter()


class EventPostPayload(BaseModel):
    message: str
    format_hint: str | None = "syslog"


class EventIngestResponse(BaseModel):
    status: str = "accepted"
    raw_event_id: str
    tenant_id: str
    source_id: str
    sha256: str


def verify_bearer_token(
    authorization: str | None = Header(None, alias="Authorization"),
    settings: Settings = get_settings(),
) -> str:
    if not authorization:
        INGEST_REJECTED_TOTAL.labels(reason="missing_auth").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        INGEST_REJECTED_TOTAL.labels(reason="invalid_auth_format").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected Bearer token.",
        )

    token = parts[1]
    if token != settings.api_auth_token:
        INGEST_REJECTED_TOTAL.labels(reason="invalid_token").inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API bearer token",
        )
    return token


async def handle_http_ingest(
    request: Request,
    authorization: str | None = Header(None, alias="Authorization"),
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    x_source_id: str | None = Header(None, alias="X-Source-ID"),
    x_source_type: str | None = Header(None, alias="X-Source-Type"),
    x_ingest_zone: str | None = Header(None, alias="X-Ingest-Zone"),
    x_collector_id: str | None = Header(None, alias="X-Collector-ID"),
) -> EventIngestResponse:
    settings: Settings = request.app.state.settings
    rate_limiter: TokenBucketRateLimiter = request.app.state.rate_limiter
    raw_vault: RawVault = request.app.state.raw_vault
    kafka_producer: KafkaProducerWrapper = request.app.state.kafka_producer
    outbox = getattr(request.app.state, "outbox", None)

    # 1. Auth check
    verify_bearer_token(authorization=authorization, settings=settings)

    # 2. Rate limit check
    await rate_limiter.check(1.0)

    # 3. Stream and bounded read of raw payload bytes (enforcing max_http_payload_bytes)
    max_bytes = settings.max_http_payload_bytes
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > max_bytes:
                INGEST_REJECTED_TOTAL.labels(reason="payload_too_large").inc()
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=f"Payload exceeds maximum allowed size of {max_bytes} bytes",
                )
        except ValueError:
            pass

    chunks = []
    total_bytes = 0
    async for chunk in request.stream():
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            INGEST_REJECTED_TOTAL.labels(reason="payload_too_large").inc()
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"Payload exceeds maximum allowed size of {max_bytes} bytes",
            )
        chunks.append(chunk)

    raw_bytes = b"".join(chunks)
    if not raw_bytes:
        INGEST_REJECTED_TOTAL.labels(reason="empty_payload").inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload body cannot be empty",
        )

    # Determine format hint from Content-Type transport metadata without modifying body
    content_type = request.headers.get("content-type", "").lower()
    format_hint = "json" if "application/json" in content_type else "syslog"

    # 4. Construct metadata
    metadata: dict[str, Any] = {
        "tenant_id": x_tenant_id or settings.default_tenant_id,
        "source_id": x_source_id or settings.default_source_id,
        "source_type": x_source_type or settings.default_source_type,
        "ingest_zone": x_ingest_zone or settings.default_ingest_zone,
        "collector_id": x_collector_id or settings.default_collector_id,
        "content_type": content_type or "text/plain",
    }

    # 5. Process through core pipeline
    envelope = await process_raw_payload(
        raw_bytes=raw_bytes,
        metadata=metadata,
        transport_protocol="http",
        transport_port=settings.http_port,
        raw_vault=raw_vault,
        kafka_producer=kafka_producer,
        format_hint=format_hint,
        bucket_name=settings.minio_bucket_raw,
        outbox=outbox,
    )

    return EventIngestResponse(
        status="accepted",
        raw_event_id=envelope.raw_event_id,
        tenant_id=envelope.tenant_id,
        source_id=envelope.source_id,
        sha256=envelope.integrity.hash,
    )
