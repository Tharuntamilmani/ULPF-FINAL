import asyncio
from typing import Any, Dict

import structlog
from fastapi import APIRouter, Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.messaging.kafka import KafkaProducerWrapper
from app.storage.raw_vault import RawVault

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check(request: Request, response: Response) -> Dict[str, str]:
    """
    Liveness probe indicating M1 application container is running.
    Never reports healthy if raw vault is uninitialized.
    """
    raw_vault = getattr(request.app.state, "raw_vault", None)
    if raw_vault is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unhealthy", "reason": "raw_vault_uninitialized"}
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check(request: Request, response: Response) -> Dict[str, Any]:
    """
    Readiness probe verifying active connectivity to MinIO raw vault and Kafka message bus.
    Fails with 503 if either dependency is down.
    """
    raw_vault: RawVault = request.app.state.raw_vault
    kafka_producer: KafkaProducerWrapper = request.app.state.kafka_producer

    try:
        minio_ok = await asyncio.wait_for(raw_vault.is_healthy(), timeout=2.0)
    except Exception as e:
        logger.warning("MinIO readiness check failed or timed out", error=str(e))
        minio_ok = False

    try:
        kafka_ok = await asyncio.wait_for(kafka_producer.is_healthy(), timeout=2.0)
    except Exception as e:
        logger.warning("Kafka readiness check failed or timed out", error=str(e))
        kafka_ok = False

    is_ready = minio_ok and kafka_ok
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    response.status_code = status_code
    return {
        "status": "ready" if is_ready else "not_ready",
        "dependencies": {
            "minio": "up" if minio_ok else "down",
            "kafka": "up" if kafka_ok else "down",
        },
    }


@router.get("/metrics")
async def metrics_endpoint() -> Response:
    """
    Prometheus metrics exposition endpoint.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
