import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.api.http_ingest import router as api_router
from app.api.rate_limiter import TokenBucketRateLimiter
from app.config.settings import get_settings
from app.health.health import router as health_router
from app.messaging.kafka import KafkaProducerWrapper
from app.storage.outbox import DurableOutbox
from app.storage.raw_vault import RawVault
from app.transports.tcp_syslog import TcpSyslogServer
from app.transports.udp_syslog import UdpSyslogServer

logger = structlog.get_logger(__name__)


class SecretScrubbingMiddleware(BaseHTTPMiddleware):
    """
    Middleware ensuring authorization headers and tokens are never logged.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Clone headers for safe logging
        safe_headers = {
            k: ("[SCRUBBED]" if k.lower() in ("authorization", "x-api-key", "token") else v)
            for k, v in request.headers.items()
        }
        logger.debug(
            "HTTP request received",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else "unknown",
            headers=safe_headers,
        )
        response = await call_next(request)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    # 1. Initialize rate limiter
    rate_limiter = TokenBucketRateLimiter(
        rate=settings.max_events_per_second,
        capacity=settings.burst_size,
    )

    # 2. Initialize MinIO Raw Vault (Mandatory)
    raw_vault = RawVault(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
        default_bucket=settings.minio_bucket_raw,
    )
    try:
        await asyncio.wait_for(raw_vault.ensure_bucket(), timeout=5.0)
        logger.info("MinIO raw vault initialized", bucket=settings.minio_bucket_raw)
    except Exception as e:
        logger.critical("MinIO raw vault mandatory initialization failed", error=str(e))
        raise RuntimeError(f"Failed to initialize mandatory raw vault: {e}") from e

    # 3. Initialize Durable Outbox for Kafka Dual-Write Safety
    outbox = DurableOutbox(db_path=settings.outbox_db_path)
    await outbox.init_db()

    # 4. Initialize Kafka Producer
    kafka_producer = KafkaProducerWrapper(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        raw_topic=settings.kafka_topic_raw,
        acks=settings.kafka_acks,
        enable_idempotence=settings.kafka_enable_idempotence,
        compression_type=settings.kafka_compression_type,
    )
    try:
        await asyncio.wait_for(kafka_producer.start(), timeout=5.0)
        logger.info("Kafka producer initialized", topic=settings.kafka_topic_raw)
    except Exception as e:
        logger.warning("Kafka producer startup deferred/unavailable at boot", error=str(e))

    # 5. Start background outbox recovery worker
    outbox.start_recovery_worker(kafka_producer, interval=2.0)

    # 6. Initialize & Start UDP Syslog listener
    udp_server = UdpSyslogServer(
        host=settings.http_host,
        port=settings.udp_port,
        settings=settings,
        raw_vault=raw_vault,
        kafka_producer=kafka_producer,
        outbox=outbox,
    )
    try:
        await udp_server.start()
    except Exception as e:
        logger.warning("UDP Syslog listener start error", error=str(e))

    # 7. Initialize & Start TCP Syslog listener
    tcp_server = TcpSyslogServer(
        host=settings.http_host,
        port=settings.tcp_port,
        settings=settings,
        raw_vault=raw_vault,
        kafka_producer=kafka_producer,
        outbox=outbox,
    )
    try:
        await tcp_server.start()
    except Exception as e:
        logger.warning("TCP Syslog listener start error", error=str(e))

    # Attach to app state
    app.state.settings = settings
    app.state.rate_limiter = rate_limiter
    app.state.raw_vault = raw_vault
    app.state.outbox = outbox
    app.state.kafka_producer = kafka_producer
    app.state.udp_server = udp_server
    app.state.tcp_server = tcp_server

    logger.info(
        "M1 Ingestion Boundary operational",
        http_port=settings.http_port,
        udp_port=settings.udp_port,
        tcp_port=settings.tcp_port,
    )

    yield

    # Shutdown sequence
    logger.info("Shutting down M1 Ingestion Boundary...")
    await outbox.close()
    await udp_server.stop()
    await tcp_server.stop()
    await kafka_producer.stop()
    logger.info("M1 shutdown clean")


app = FastAPI(
    title="ULPF M1 - Ingestion Boundary Service",
    description="Universal Log Preprocessing Framework (M1) Ingestion & Raw Evidence Preservation Boundary",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(SecretScrubbingMiddleware)
app.include_router(health_router)
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    config = get_settings()
    uvicorn.run(
        "app.main:app",
        host=config.http_host,
        port=config.http_port,
        reload=False,
    )
