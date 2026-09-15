import json

import httpx
import pytest
import pytest_asyncio

from app.api.rate_limiter import TokenBucketRateLimiter
from app.config.settings import Settings
from app.integrity.hashing import compute_sha256
from app.main import app


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


@pytest_asyncio.fixture
async def setup_app():
    vault = MockRawVault()
    kafka = MockKafkaProducer()
    settings = Settings()
    settings.api_auth_token = "valid-token-123"
    settings.max_http_payload_bytes = 2 * 1024 * 1024  # 2MB

    app.state.settings = settings
    app.state.rate_limiter = TokenBucketRateLimiter(rate=5000.0, capacity=10000.0)
    app.state.raw_vault = vault
    app.state.kafka_producer = kafka
    app.state.outbox = None

    yield vault, kafka


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload_bytes,headers,expected_hint",
    [
        (
            b"<134>Sep 13 20:00:00 FW-01 test: hello",
            {"Content-Type": "text/plain"},
            "syslog",
        ),
        (
            b'{"event": "CloudTrail", "userIdentity": "arn:aws:iam::123:root"}',
            {"Content-Type": "application/json"},
            "json",
        ),
        (
            json.dumps({"okta": {"actor": "admin@domain.com", "nested": {"level": 2}}}).encode(
                "utf-8"
            ),
            {"Content-Type": "application/json"},
            "json",
        ),
        (
            "CrowdStrike Alert: 🚨 恶意进程 detected".encode(),
            {"Content-Type": "text/plain; charset=utf-8"},
            "syslog",
        ),
        (
            b"\x00\x01\x02\xfe\xff\x80\x81\xde\xad\xbe\xef",
            {"Content-Type": "application/octet-stream"},
            "syslog",
        ),
        (
            b"Plain syslog message with no content-type header",
            {},  # Omitted Content-Type
            "syslog",
        ),
    ],
    ids=[
        "plain_text_syslog",
        "arbitrary_json",
        "nested_json",
        "unicode_utf8",
        "binary_bytes",
        "content_type_omitted",
    ],
)
async def test_http_raw_ingestion_accepts_arbitrary_payloads(
    setup_app, payload_bytes: bytes, headers: dict, expected_hint: str
):
    """
    P0-1 Verification:
    HTTP endpoint must accept arbitrary raw request bodies without pydantic binding failures.
    Exact bytes must be captured into MinIO raw vault and envelope SHA-256 must match.
    """
    vault, kafka = setup_app

    req_headers = {
        "Authorization": "Bearer valid-token-123",
        "X-Tenant-ID": "test-corp",
        "X-Source-ID": "src-42",
    }
    req_headers.update(headers)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/v1/events",
            content=payload_bytes,
            headers=req_headers,
        )

        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "accepted"
        assert body["sha256"] == compute_sha256(payload_bytes)

        # Verify envelope in Kafka
        assert len(kafka.published) > 0
        envelope = kafka.published[-1]
        assert envelope.integrity.hash == compute_sha256(payload_bytes)
        assert envelope.payload.format_hint == expected_hint

        # Verify byte-for-byte exact payload in raw vault
        stored = await vault.get_raw_event(
            envelope.raw_storage.bucket, envelope.raw_storage.object_key
        )
        assert stored == payload_bytes


@pytest.mark.asyncio
async def test_http_raw_empty_payload_rejected(setup_app):
    """Empty body must be rejected with HTTP 400."""
    vault, kafka = setup_app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/v1/events",
            content=b"",
            headers={"Authorization": "Bearer valid-token-123"},
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "size_bytes,should_succeed",
    [
        (100, True),
        (4 * 1024, True),
        (64 * 1024, True),
        (1024 * 1024, True),
        (2 * 1024 * 1024, True),  # Exactly 2 MB boundary
        (2 * 1024 * 1024 + 1, False),  # > 2 MB by 1 byte
        (3 * 1024 * 1024, False),  # 3 MB
    ],
    ids=["100B", "4KB", "64KB", "1MB", "2MB_boundary", "2MB_plus_1B", "3MB"],
)
async def test_http_payload_size_limits(setup_app, size_bytes: int, should_succeed: bool):
    """
    P0-5 Verification:
    2 MB maximum HTTP request body.
    Oversized requests must return HTTP 413 Payload Too Large.
    """
    vault, kafka = setup_app
    payload = b"X" * size_bytes

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/v1/events",
            content=payload,
            headers={
                "Authorization": "Bearer valid-token-123",
                "Content-Type": "application/octet-stream",
            },
        )

        if should_succeed:
            assert resp.status_code == 202
            assert resp.json()["status"] == "accepted"
        else:
            assert resp.status_code == 413
            assert "exceeds maximum allowed size" in resp.json()["detail"].lower()
