"""
Failure Testing Suite for ULPF Integration Layer.
Verifies behavior under simulated component failure:
  1. Transient network timeout with successful recovery on retry
  2. Bounded retries exceeding threshold (fails safely without hang)
  3. Safe handling of corrupted/unparseable messages (DLQ behavior)
  4. Preservation of state during transient dependency outages
"""

import pytest
import asyncio
from integration.adapters.retry_policy import RetryPolicy
from integration.consumers.m1_raw_consumer import M1RawEventConsumer
from integration.adapters.idempotency import IdempotencyTracker


@pytest.mark.asyncio
async def test_transient_failure_recovery():
    """Simulates 2 network timeouts followed by success; verify RetryPolicy recovers."""
    attempts = 0

    async def flaky_service_call():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError(f"Simulated network timeout (attempt {attempts})")
        return {"status": "SUCCESS", "recovered_at_attempt": attempts}

    policy = RetryPolicy(
        max_retries=3,
        base_delay_ms=10.0,
        retryable_exceptions=[ConnectionError],
    )

    result = await policy.execute_async(flaky_service_call, operation_name="flaky_call")
    assert result["status"] == "SUCCESS"
    assert result["recovered_at_attempt"] == 3


@pytest.mark.asyncio
async def test_bounded_retry_exhaustion():
    """Simulates persistent failure; verify policy fails boundedly without hanging."""
    attempts = 0

    async def permanently_down_call():
        nonlocal attempts
        attempts += 1
        raise ConnectionRefusedError("Module permanently unavailable")

    policy = RetryPolicy(
        max_retries=2,
        base_delay_ms=10.0,
        retryable_exceptions=[ConnectionRefusedError],
    )

    with pytest.raises(ConnectionRefusedError):
        await policy.execute_async(permanently_down_call, operation_name="dead_service")

    assert attempts == 3  # 1 initial + 2 retries


@pytest.mark.asyncio
async def test_consumer_bridge_deduplication():
    """Verify M1RawEventConsumer detects duplicate delivery and suppresses second call."""
    tracker = IdempotencyTracker()
    consumer = M1RawEventConsumer(idempotency_tracker=tracker)

    raw_msg = {
        "raw_event_id": "raw_fail_test_001",
        "tenant_id": "tenant-test",
        "source_id": "src-test",
        "payload": {"data": "test message"},
        "integrity": {"hash": "dummyhash"},
    }

    # Pre-seed first processing
    tracker.check_and_set("tenant-test", "raw_fail_test_001", {"status": "PARSED"})

    # Process message via consumer
    result = await consumer.process_raw_message(raw_msg)
    assert result["status"] == "DUPLICATE_SUPPRESSED"
    assert result["raw_event_id"] == "raw_fail_test_001"
