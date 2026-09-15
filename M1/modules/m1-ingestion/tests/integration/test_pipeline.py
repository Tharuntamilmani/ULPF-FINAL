import httpx
import pytest

from app.api.rate_limiter import TokenBucketRateLimiter
from app.config.settings import Settings
from app.integrity.hashing import compute_sha256
from app.main import app
from app.transports.pipeline import process_raw_payload


class MockRawVault:
    def __init__(self):
        self.storage = {}

    async def store_raw_event(self, bucket: str, object_key: str, payload_bytes: bytes):
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
        return True


class MockKafkaProducer:
    def __init__(self):
        self.published = []
        self.raw_topic = "ulpf.raw"

    async def publish_envelope(self, envelope, topic=None):
        self.published.append(envelope)
        return {"topic": topic or self.raw_topic, "partition": 0, "offset": len(self.published)}

    async def is_healthy(self):
        return True


@pytest.mark.asyncio
async def test_essential_sha256_roundtrip_preservation():
    """
    CRITICAL INTEGRITY TEST:
    1. Send raw payload "hello world"
    2. Compute original SHA-256 hash
    3. Store payload via RawVault
    4. Retrieve and decompress payload from RawVault
    5. Assert stored_sha256 == original_sha256 and decompressed_bytes == original_bytes
    """
    raw_bytes = b"hello world"
    original_sha256 = compute_sha256(raw_bytes)

    vault = MockRawVault()
    kafka = MockKafkaProducer()

    metadata = {
        "tenant_id": "demo-tenant",
        "source_id": "test-cisco-01",
    }

    envelope = await process_raw_payload(
        raw_bytes=raw_bytes,
        metadata=metadata,
        transport_protocol="http",
        transport_port=8000,
        raw_vault=vault,  # type: ignore
        kafka_producer=kafka,  # type: ignore
        bucket_name="ulpf-raw",
    )

    # Verify Envelope SHA256 matches
    assert envelope.integrity.hash == original_sha256

    # Retrieve stored payload from raw vault
    retrieved_bytes = await vault.get_raw_event(
        envelope.raw_storage.bucket, envelope.raw_storage.object_key
    )
    retrieved_sha256 = compute_sha256(retrieved_bytes)

    # Exact byte & SHA-256 equality assertions
    assert retrieved_bytes == raw_bytes
    assert retrieved_sha256 == original_sha256
    assert len(kafka.published) == 1
    assert kafka.published[0].raw_event_id == envelope.raw_event_id


@pytest.mark.asyncio
async def test_http_api_auth_and_rejection():
    vault = MockRawVault()
    kafka = MockKafkaProducer()

    settings = Settings()
    settings.api_auth_token = "test-bearer-token-xyz"
    app.state.settings = settings
    app.state.rate_limiter = TokenBucketRateLimiter(rate=1000.0, capacity=2000.0)
    app.state.raw_vault = vault
    app.state.kafka_producer = kafka

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Test missing auth header -> 401
        resp = await client.post("/v1/events", json={"message": "test event"})
        assert resp.status_code == 401

        # 2. Test invalid bearer token -> 403
        resp = await client.post(
            "/v1/events",
            json={"message": "test event"},
            headers={"Authorization": "Bearer bad-token-xyz"},
        )
        assert resp.status_code == 403

        # 3. Test valid auth -> 202 Accepted
        resp = await client.post(
            "/v1/events",
            json={"message": "<134>Sep 12 09:30:15 FW-01 test log line"},
            headers={
                "Authorization": "Bearer test-bearer-token-xyz",
                "X-Tenant-ID": "test-tenant",
                "X-Source-ID": "fw-01",
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "accepted"
        assert "raw_event_id" in data
        assert data["tenant_id"] == "test-tenant"
        assert len(data["sha256"]) == 64
