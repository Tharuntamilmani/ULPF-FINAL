"""OpenSearch client — used for audit log indexing and health checks."""

from __future__ import annotations

from typing import Any

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger

logger = get_logger("opensearch_client")


async def get_opensearch_client() -> Any:
    settings = get_settings()
    try:
        from opensearchpy import AsyncOpenSearch

        return AsyncOpenSearch(
            hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
            http_auth=(settings.opensearch_user, settings.opensearch_password),
            use_ssl=settings.opensearch_use_ssl,
            verify_certs=settings.opensearch_verify_certs,
            timeout=10,
        )
    except Exception as exc:
        logger.warning("OpenSearch client creation failed", error=str(exc))
        return None
