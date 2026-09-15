import asyncio
import time

from fastapi import HTTPException, status


class TokenBucketRateLimiter:
    """
    Token-bucket rate limiter enforcing max events per second and burst capacity.
    """

    def __init__(self, rate: float = 1000.0, capacity: float = 2000.0):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def consume(self, tokens: float = 1.0) -> bool:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now

            # Replenish tokens based on elapsed time
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    async def check(self, tokens: float = 1.0) -> None:
        allowed = await self.consume(tokens)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )
