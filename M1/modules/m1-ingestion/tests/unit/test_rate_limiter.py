import pytest
from fastapi import HTTPException

from app.api.rate_limiter import TokenBucketRateLimiter


@pytest.mark.asyncio
async def test_token_bucket_limiter_burst_and_exhaustion():
    limiter = TokenBucketRateLimiter(rate=1.0, capacity=2.0)

    # Consume available capacity
    assert await limiter.consume(1.0) is True
    assert await limiter.consume(1.0) is True

    # Next attempt should fail
    assert await limiter.consume(1.0) is False

    with pytest.raises(HTTPException) as exc_info:
        await limiter.check(1.0)
    assert exc_info.value.status_code == 429
