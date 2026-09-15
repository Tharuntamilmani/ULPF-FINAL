"""MinIO client — used for contract/schema artifact storage."""

from __future__ import annotations

from typing import Any

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger

logger = get_logger("minio_client")


def get_minio_client() -> Any:
    settings = get_settings()
    try:
        from minio import Minio

        return Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    except Exception as exc:
        logger.warning("MinIO client creation failed", error=str(exc))
        return None
