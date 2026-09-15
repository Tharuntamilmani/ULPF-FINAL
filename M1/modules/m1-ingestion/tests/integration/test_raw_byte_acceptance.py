import asyncio
import socket
from pathlib import Path

import httpx
import pytest

from app.api.rate_limiter import TokenBucketRateLimiter
from app.config.settings import Settings
from app.integrity.hashing import compute_sha256
from app.main import app
from app.transports.file_replay import replay_file
from app.transports.tcp_syslog import TcpSyslogServer
from app.transports.udp_syslog import UdpSyslogServer


class MemoryRawVault:
    """In-memory MinIO vault simulator preserving raw gzip-compressed byte store."""

    def __init__(self):
        self.objects = {}

    async def store_raw_event(self, bucket: str, object_key: str, payload_bytes: bytes):
        import gzip

        compressed = gzip.compress(payload_bytes)
        self.objects[f"{bucket}/{object_key}"] = compressed
        return {
            "bucket": bucket,
            "object_key": object_key,
            "compressed_size": len(compressed),
            "original_size": len(payload_bytes),
        }

    async def get_raw_event(self, bucket: str, object_key: str) -> bytes:
        import gzip

        compressed = self.objects[f"{bucket}/{object_key}"]
        return gzip.decompress(compressed)

    async def is_healthy(self, bucket=None):
        return True


class MemoryKafkaProducer:
    def __init__(self):
        self.published = []
        self.raw_topic = "ulpf.raw"

    async def publish_envelope(self, envelope, topic=None):
        self.published.append(envelope)
        return {"topic": self.raw_topic, "partition": 0, "offset": len(self.published)}

    async def is_healthy(self):
        return True


CANONICAL_PAYLOAD = b"<134>Sep 13 20:00:00 FW-01 test: hello"
CANONICAL_SHA256 = compute_sha256(CANONICAL_PAYLOAD)


@pytest.mark.asyncio
async def test_canonical_raw_byte_acceptance_http():
    """
    CANONICAL ACCEPTANCE TEST — HTTP:
    Payload: <134>Sep 13 20:00:00 FW-01 test: hello
    Verify: original SHA-256 == stored SHA-256 AND original bytes == retrieved raw bytes
    """
    vault = MemoryRawVault()
    kafka = MemoryKafkaProducer()
    settings = Settings()
    settings.api_auth_token = "m1-token"

    app.state.settings = settings
    app.state.rate_limiter = TokenBucketRateLimiter(rate=1000.0, capacity=2000.0)
    app.state.raw_vault = vault
    app.state.kafka_producer = kafka
    app.state.outbox = None

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/v1/events",
            content=CANONICAL_PAYLOAD,
            headers={
                "Authorization": "Bearer m1-token",
                "Content-Type": "text/plain",
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["sha256"] == CANONICAL_SHA256

        # Retrieve stored raw payload from vault
        envelope = kafka.published[-1]
        assert envelope.integrity.hash == CANONICAL_SHA256
        retrieved_bytes = await vault.get_raw_event(
            envelope.raw_storage.bucket, envelope.raw_storage.object_key
        )

        assert retrieved_bytes == CANONICAL_PAYLOAD
        assert compute_sha256(retrieved_bytes) == CANONICAL_SHA256


@pytest.mark.asyncio
async def test_canonical_raw_byte_acceptance_tcp():
    """
    CANONICAL ACCEPTANCE TEST — TCP Syslog:
    Payload: <134>Sep 13 20:00:00 FW-01 test: hello
    Verify: original SHA-256 == stored SHA-256 AND original bytes == retrieved raw bytes
    """
    vault = MemoryRawVault()
    kafka = MemoryKafkaProducer()
    settings = Settings()

    test_port = 15158
    server = TcpSyslogServer(
        host="127.0.0.1",
        port=test_port,
        settings=settings,
        raw_vault=vault,  # type: ignore
        kafka_producer=kafka,  # type: ignore
    )
    await server.start()

    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", test_port)
        writer.write(CANONICAL_PAYLOAD)
        await writer.drain()
        writer.close()
        await writer.wait_closed()

        await asyncio.sleep(0.1)

        assert len(kafka.published) == 1
        envelope = kafka.published[0]
        assert envelope.integrity.hash == CANONICAL_SHA256

        retrieved_bytes = await vault.get_raw_event(
            envelope.raw_storage.bucket, envelope.raw_storage.object_key
        )
        assert retrieved_bytes == CANONICAL_PAYLOAD
        assert compute_sha256(retrieved_bytes) == CANONICAL_SHA256
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_canonical_raw_byte_acceptance_udp():
    """
    CANONICAL ACCEPTANCE TEST — UDP Syslog:
    Payload: <134>Sep 13 20:00:00 FW-01 test: hello
    Verify: original SHA-256 == stored SHA-256 AND original bytes == retrieved raw bytes
    """
    vault = MemoryRawVault()
    kafka = MemoryKafkaProducer()
    settings = Settings()
    settings.udp_queue_size = 100
    settings.udp_workers = 2

    test_port = 15159
    server = UdpSyslogServer(
        host="127.0.0.1",
        port=test_port,
        settings=settings,
        raw_vault=vault,  # type: ignore
        kafka_producer=kafka,  # type: ignore
    )
    await server.start()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(CANONICAL_PAYLOAD, ("127.0.0.1", test_port))
        sock.close()

        await asyncio.sleep(0.1)

        assert len(kafka.published) == 1
        envelope = kafka.published[0]
        assert envelope.integrity.hash == CANONICAL_SHA256

        retrieved_bytes = await vault.get_raw_event(
            envelope.raw_storage.bucket, envelope.raw_storage.object_key
        )
        assert retrieved_bytes == CANONICAL_PAYLOAD
        assert compute_sha256(retrieved_bytes) == CANONICAL_SHA256
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_canonical_raw_byte_acceptance_file_replay(tmp_path: Path):
    """
    CANONICAL ACCEPTANCE TEST — File Replay:
    Payload: <134>Sep 13 20:00:00 FW-01 test: hello
    Verify: original SHA-256 == stored SHA-256 AND original bytes == retrieved raw bytes
    """
    vault = MemoryRawVault()
    kafka = MemoryKafkaProducer()
    settings = Settings()

    log_file = tmp_path / "canonical.log"
    log_file.write_bytes(CANONICAL_PAYLOAD)

    envelopes = await replay_file(
        file_path=log_file,
        settings=settings,
        raw_vault=vault,  # type: ignore
        kafka_producer=kafka,  # type: ignore
    )

    assert len(envelopes) == 1
    envelope = envelopes[0]
    assert envelope.integrity.hash == CANONICAL_SHA256

    retrieved_bytes = await vault.get_raw_event(
        envelope.raw_storage.bucket, envelope.raw_storage.object_key
    )
    assert retrieved_bytes == CANONICAL_PAYLOAD
    assert compute_sha256(retrieved_bytes) == CANONICAL_SHA256
