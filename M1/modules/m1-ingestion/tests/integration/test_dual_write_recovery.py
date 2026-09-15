from pathlib import Path

import httpx
import pytest
import pytest_asyncio

from app.integrity.hashing import compute_sha256
from app.main import app, lifespan
from app.storage.outbox import DurableOutbox
from app.transports.pipeline import (
    KafkaPublishError,
    MinIOWriteError,
    process_raw_payload,
)


class MockRawVault:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.storage = {}

    async def ensure_bucket(self, bucket=None):
        if self.should_fail:
            raise ConnectionError("Cannot reach MinIO cluster")

    async def store_raw_event(self, bucket: str, object_key: str, payload_bytes: bytes):
        if self.should_fail:
            raise ConnectionError("MinIO storage failed")
        import gzip

        compressed = gzip.compress(payload_bytes)
        self.storage[f"{bucket}/{object_key}"] = compressed
        return {
            "bucket": bucket,
            "object_key": object_key,
            "compressed_size": len(compressed),
            "original_size": len(payload_bytes),
        }

    async def get_raw_event(self, bucket: str, object_key: str) -> bytes:
        import gzip

        compressed = self.storage[f"{bucket}/{object_key}"]
        return gzip.decompress(compressed)

    async def is_healthy(self, bucket=None):
        return not self.should_fail


class MockFailingKafkaProducer:
    def __init__(self, should_fail: bool = True):
        self.should_fail = should_fail
        self.raw_topic = "ulpf.raw"
        self.published = []

    async def start(self):
        if self.should_fail:
            raise ConnectionError("Kafka cluster unreachable")

    async def publish_envelope(self, envelope, topic=None):
        if self.should_fail:
            raise ConnectionError("Kafka publish timeout: broker unavailable")
        self.published.append(envelope)
        return {"topic": "ulpf.raw", "partition": 0, "offset": len(self.published)}

    async def is_healthy(self):
        return not self.should_fail


@pytest_asyncio.fixture
async def outbox(tmp_path: Path):
    db_file = tmp_path / "dual_write_outbox.db"
    box = DurableOutbox(db_path=str(db_file))
    await box.init_db()
    yield box
    await box.close()


@pytest.mark.asyncio
async def test_dual_write_minio_up_kafka_down_spools_to_outbox(outbox: DurableOutbox):
    """
    P1 Verification:
    MinIO write succeeds, Kafka publish fails.
    The raw object must NOT be deleted from MinIO.
    The envelope must be spooled to the durable outbox for deferred replay.
    """
    raw_vault = MockRawVault(should_fail=False)
    failing_kafka = MockFailingKafkaProducer(should_fail=True)

    raw_bytes = b"<134>Sep 13 20:30:00 FW-01 test log during kafka outage\n"
    metadata = {"tenant_id": "test-tenant", "source_id": "fw-01"}

    # Pipeline must catch Kafka error, spool to outbox, and raise KafkaPublishError
    with pytest.raises(KafkaPublishError):
        await process_raw_payload(
            raw_bytes=raw_bytes,
            metadata=metadata,
            transport_protocol="http",
            transport_port=8000,
            raw_vault=raw_vault,  # type: ignore
            kafka_producer=failing_kafka,  # type: ignore
            bucket_name="ulpf-raw",
            outbox=outbox,
        )

    # 1. Assert raw object exists safely in MinIO vault (no orphan / no loss)
    assert len(raw_vault.storage) == 1
    stored_key = list(raw_vault.storage.keys())[0]
    bucket, object_key = stored_key.split("/", 1)
    retrieved = await raw_vault.get_raw_event(bucket, object_key)
    assert retrieved == raw_bytes

    # 2. Assert envelope was spooled to outbox
    pending = await outbox.get_pending_records(limit=10)
    assert len(pending) == 1
    assert pending[0]["raw_object_key"] == object_key
    assert pending[0]["status"] == "pending"

    # 3. Recovery Phase: Kafka recovers, replay pending outbox
    recovered_kafka = MockFailingKafkaProducer(should_fail=False)
    replayed = await outbox.replay_pending(recovered_kafka, batch_size=10)  # type: ignore
    assert replayed == 1
    assert len(recovered_kafka.published) == 1
    assert recovered_kafka.published[0].integrity.hash == compute_sha256(raw_bytes)

    # 4. Assert outbox pending count is now 0
    pending_after = await outbox.get_pending_records(limit=10)
    assert len(pending_after) == 0


@pytest.mark.asyncio
async def test_dual_write_minio_down_kafka_up(outbox: DurableOutbox):
    """
    MinIO write fails: pipeline must raise MinIOWriteError immediately.
    Kafka publish is never attempted. Outbox is not spooled.
    """
    failing_vault = MockRawVault(should_fail=True)
    good_kafka = MockFailingKafkaProducer(should_fail=False)

    with pytest.raises(MinIOWriteError):
        await process_raw_payload(
            raw_bytes=b"log payload",
            metadata={"tenant_id": "t1", "source_id": "s1"},
            transport_protocol="http",
            transport_port=8000,
            raw_vault=failing_vault,  # type: ignore
            kafka_producer=good_kafka,  # type: ignore
            outbox=outbox,
        )

    assert len(good_kafka.published) == 0
    pending = await outbox.get_pending_records(limit=10)
    assert len(pending) == 0


@pytest.mark.asyncio
async def test_lifespan_mandatory_raw_vault_failure():
    """
    P0-2 Verification:
    If raw vault initialization fails, lifespan must NOT swallow the error.
    It must log and fail startup immediately.
    """
    from unittest.mock import patch

    # Mock RawVault.ensure_bucket to fail
    with patch(
        "app.main.RawVault.ensure_bucket", side_effect=ConnectionError("MinIO connection refused")
    ):
        with pytest.raises(RuntimeError) as exc_info:
            async with lifespan(app):
                pass
        assert "mandatory raw vault" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_health_endpoint_reports_unhealthy_when_uninitialized():
    """
    P0-2 Verification:
    Service must NEVER report healthy if raw vault is uninitialized.
    """
    # Clean app state
    app.state.raw_vault = None

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/health")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unhealthy"
        assert data["reason"] == "raw_vault_uninitialized"
