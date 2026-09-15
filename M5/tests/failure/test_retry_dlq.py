"""
Failure handling tests for RetryEngine and DeadLetterQueue.
Verifies retry backoff, eventual success, retry exhaustion failover to DLQ,
and immediate DLQ promotion on permanent non-retryable errors.
"""
from typing import Any, Dict
from app.connectors.base import DestinationConnector
from app.delivery.ack import AckTracker, DeliveryState
from app.delivery.dlq import DeadLetterQueue
from app.delivery.retry import RetryEngine


class FlakyConnector(DestinationConnector):
    def __init__(self, fail_count: int = 1, name_str: str = "flaky_dest"):
        self._name = name_str
        self.fail_count = fail_count
        self.attempts = 0

    def name(self) -> str:
        return self._name

    async def send(self, event: Dict[str, Any]) -> None:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise ConnectionError(f"Simulated transient error attempt {self.attempts}")

    async def health(self) -> bool:
        return True


class PermanentFailConnector(DestinationConnector):
    def __init__(self, name_str: str = "strict_dest"):
        self._name = name_str
        self.attempts = 0

    def name(self) -> str:
        return self._name

    async def send(self, event: Dict[str, Any]) -> None:
        self.attempts += 1
        raise ValueError("Permanent schema incompatible error")

    async def health(self) -> bool:
        return True


async def test_retry_success_on_second_attempt():
    ack_tracker = AckTracker()
    dlq = DeadLetterQueue()
    engine = RetryEngine(
        max_retries=3,
        initial_backoff_sec=0.01,
        ack_tracker=ack_tracker,
        dlq=dlq
    )

    connector = FlakyConnector(fail_count=1, name_str="flaky_service")
    event = {"event": {"id": "evt_retry_01"}}

    success = await engine.deliver_to_connector(connector, event)

    assert success is True
    assert connector.attempts == 2
    status = ack_tracker.get_status("evt_retry_01", "flaky_service")
    assert status is not None
    assert status.status == DeliveryState.ACKNOWLEDGED
    assert status.attempts == 2
    # Ensure nothing pushed to DLQ
    assert len(dlq.get_records()) == 0


async def test_retry_exhaustion_promotes_to_dlq():
    ack_tracker = AckTracker()
    dlq = DeadLetterQueue()
    engine = RetryEngine(
        max_retries=3,
        initial_backoff_sec=0.01,
        ack_tracker=ack_tracker,
        dlq=dlq
    )

    # Connector fails 5 times (exceeds max_retries=3)
    connector = FlakyConnector(fail_count=5, name_str="broken_dest")
    event = {"event": {"id": "evt_dlq_01"}}

    success = await engine.deliver_to_connector(connector, event)

    assert success is False
    assert connector.attempts == 3
    status = ack_tracker.get_status("evt_dlq_01", "broken_dest")
    assert status is not None
    assert status.status == DeliveryState.DLQ_PROMOTED

    records = dlq.get_records()
    assert len(records) >= 1
    last_rec = records[-1]
    assert last_rec.event_id == "evt_dlq_01"
    assert last_rec.destination == "broken_dest"
    assert last_rec.attempts == 3
    assert last_rec.failure_code == "DESTINATION_UNAVAILABLE"


async def test_permanent_error_promotes_immediately_to_dlq():
    ack_tracker = AckTracker()
    dlq = DeadLetterQueue()
    engine = RetryEngine(
        max_retries=3,
        initial_backoff_sec=0.01,
        ack_tracker=ack_tracker,
        dlq=dlq
    )

    connector = PermanentFailConnector(name_str="strict_dest")
    event = {"event": {"id": "evt_perm_01"}}

    success = await engine.deliver_to_connector(connector, event)

    assert success is False
    # Crucial: Permanent errors should NOT be retried!
    assert connector.attempts == 1
    status = ack_tracker.get_status("evt_perm_01", "strict_dest")
    assert status is not None
    assert status.status == DeliveryState.DLQ_PROMOTED

    records = dlq.get_records()
    assert len(records) >= 1
    last_rec = records[-1]
    assert last_rec.event_id == "evt_perm_01"
    assert last_rec.destination == "strict_dest"
    assert last_rec.attempts == 1
    assert last_rec.failure_code == "PERMANENT_SCHEMA_ERROR"
