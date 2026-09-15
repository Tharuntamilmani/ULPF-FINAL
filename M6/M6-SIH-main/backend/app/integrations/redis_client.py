"""
Redis client — async connection pool with health-check support.
Used by ConfigDistributionService for config key publishing.
"""

from __future__ import annotations

import redis.asyncio as aioredis

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger

logger = get_logger("redis")
_client: aioredis.Redis | None = None  # type: ignore[type-arg]


async def get_redis_client() -> aioredis.Redis:  # type: ignore[type-arg]
    global _client
    if _client is None:
        settings = get_settings()
        _client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        close_fn = getattr(_client, "aclose", getattr(_client, "close", None))
        if close_fn is not None:
            await close_fn()
        _client = None


async def redis_ping() -> bool:
    """Return True if Redis is reachable."""
    try:
        client = await get_redis_client()
        return await client.ping()
    except Exception as exc:
        logger.warning("Redis ping failed", error=str(exc))
        return False
