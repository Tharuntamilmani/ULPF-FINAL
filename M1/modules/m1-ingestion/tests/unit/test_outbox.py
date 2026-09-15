from pathlib import Path

import pytest
import pytest_asyncio

from app.envelope.builder import build_envelope
from app.storage.outbox import DurableOutbox


@pytest_asyncio.fixture
async def outbox(tmp_path: Path):
    db_file = tmp_path / "test_outbox.db"
    box = DurableOutbox(db_path=str(db_file))
    await box.init_db()
    yield box
    await box.close()


@pytest.mark.asyncio
async def test_outbox_spool_and_fetch_pending(outbox: DurableOutbox):
    envelope = build_envelope(
        raw_bytes=b"syslog test message",
        metadata={"tenant_id": "t1", "source_id": "s1"},
        transport_protocol="http",
    )

    # Initially empty
    pending = await outbox.get_pending_records(limit=10)
    assert len(pending) == 0

    # Spool envelope
    await outbox.spool_envelope(
        envelope=envelope,
        raw_object_key=envelope.raw_storage.object_key,
        topic="ulpf.raw",
        error_reason="Kafka connection refused",
    )

    # Fetch pending
    pending = await outbox.get_pending_records(limit=10)
    assert len(pending) == 1
    rec = pending[0]
    assert rec["raw_event_id"] == envelope.raw_event_id
    assert rec["raw_object_key"] == envelope.raw_storage.object_key
    assert rec["topic"] == "ulpf.raw"
    assert rec["status"] == "pending"
    assert rec["attempts"] == 0

    # Mark replayed
    await outbox.mark_replayed(rec["raw_event_id"])

    # Pending should now be 0
    pending_after = await outbox.get_pending_records(limit=10)
    assert len(pending_after) == 0


@pytest.mark.asyncio
async def test_outbox_replay_pending(outbox: DurableOutbox):
    envelope = build_envelope(
        raw_bytes=b"syslog test message for recovery",
        metadata={"tenant_id": "t1", "source_id": "s1"},
        transport_protocol="http",
    )

    await outbox.spool_envelope(
        envelope=envelope,
        raw_object_key=envelope.raw_storage.object_key,
        topic="ulpf.raw",
        error_reason="Kafka timeout",
    )

    # Mock kafka producer
    class MockKafka:
        def __init__(self):
            self.published = []

        async def publish_envelope(self, env, topic=None):
            self.published.append((env, topic))
            return {"status": "ok"}

    mock_kafka = MockKafka()
    replayed_count = await outbox.replay_pending(mock_kafka, batch_size=10)  # type: ignore

    assert replayed_count == 1
    assert len(mock_kafka.published) == 1
    pub_env, pub_topic = mock_kafka.published[0]
    assert pub_env.raw_event_id == envelope.raw_event_id
    assert pub_topic == "ulpf.raw"

    # Subsequent replay should find 0 pending
    replayed_count_2 = await outbox.replay_pending(mock_kafka, batch_size=10)  # type: ignore
    assert replayed_count_2 == 0
