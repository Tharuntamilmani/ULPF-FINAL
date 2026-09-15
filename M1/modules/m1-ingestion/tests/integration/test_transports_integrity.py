import asyncio
from pathlib import Path

import pytest

from app.config.settings import Settings
from app.integrity.hashing import compute_sha256
from app.transports.file_replay import replay_file
from app.transports.tcp_syslog import TcpSyslogServer
from app.transports.udp_syslog import UdpSyslogServer


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
async def test_file_replay_preserves_exact_bytes_and_newlines(tmp_path: Path):
    """
    P0-3 Verification for File Replay:
    Line endings (\\n, \\r\\n) and raw content must NOT be stripped.
    """
    vault = MockRawVault()
    kafka = MockKafkaProducer()
    settings = Settings()

    # Create a test log file containing lines with distinct endings
    log_content = (
        b"line_without_ending"
        + b"\n"
        + b"crlf_line\r\n"
        + b"unicode_alert: \xe6\xad\xa3\xe5\xb8\xb8\n"
    )
    test_file = tmp_path / "test_replay.log"
    test_file.write_bytes(log_content)

    envelopes = await replay_file(
        file_path=test_file,
        settings=settings,
        raw_vault=vault,  # type: ignore
        kafka_producer=kafka,  # type: ignore
    )

    assert len(envelopes) == 3

    # Line 1: line_without_ending\n
    stored_1 = await vault.get_raw_event(
        envelopes[0].raw_storage.bucket, envelopes[0].raw_storage.object_key
    )
    assert stored_1 == b"line_without_ending\n"
    assert envelopes[0].integrity.hash == compute_sha256(b"line_without_ending\n")

    # Line 2: crlf_line\r\n
    stored_2 = await vault.get_raw_event(
        envelopes[1].raw_storage.bucket, envelopes[1].raw_storage.object_key
    )
    assert stored_2 == b"crlf_line\r\n"
    assert envelopes[1].integrity.hash == compute_sha256(b"crlf_line\r\n")

    # Line 3: unicode_alert: 正常\n
    stored_3 = await vault.get_raw_event(
        envelopes[2].raw_storage.bucket, envelopes[2].raw_storage.object_key
    )
    assert stored_3 == b"unicode_alert: \xe6\xad\xa3\xe5\xb8\xb8\n"
    assert envelopes[2].integrity.hash == compute_sha256(
        b"unicode_alert: \xe6\xad\xa3\xe5\xb8\xb8\n"
    )


@pytest.mark.asyncio
async def test_tcp_syslog_preserves_exact_raw_bytes():
    """
    P0-3 Verification for TCP Syslog:
    b"hello\\n" and b"hello\\r\\n" must preserve exact bytes without rstrip.
    """
    vault = MockRawVault()
    kafka = MockKafkaProducer()
    settings = Settings()

    # Use port 15155 for local test
    test_port = 15155
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
        # Send line ending with \n
        writer.write(b"<134>hello\n")
        # Send line ending with \r\n
        writer.write(b"<134>hello\r\n")
        await writer.drain()
        writer.close()
        await writer.wait_closed()

        # Allow server to process lines
        await asyncio.sleep(0.1)

        assert len(kafka.published) == 2
        env1 = kafka.published[0]
        env2 = kafka.published[1]

        # Verify exact stored bytes
        stored1 = await vault.get_raw_event(env1.raw_storage.bucket, env1.raw_storage.object_key)
        assert stored1 == b"<134>hello\n"
        assert env1.integrity.hash == compute_sha256(b"<134>hello\n")

        stored2 = await vault.get_raw_event(env2.raw_storage.bucket, env2.raw_storage.object_key)
        assert stored2 == b"<134>hello\r\n"
        assert env2.integrity.hash == compute_sha256(b"<134>hello\r\n")
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_udp_syslog_preserves_exact_raw_bytes():
    """
    P0-3 Verification for UDP Syslog:
    UDP datagram bytes must be captured 100% untouched.
    """
    vault = MockRawVault()
    kafka = MockKafkaProducer()
    settings = Settings()
    settings.udp_queue_size = 100
    settings.udp_workers = 2

    test_port = 15156
    server = UdpSyslogServer(
        host="127.0.0.1",
        port=test_port,
        settings=settings,
        raw_vault=vault,  # type: ignore
        kafka_producer=kafka,  # type: ignore
    )
    await server.start()

    try:
        loop = asyncio.get_running_loop()
        test_payload = b"<134>Sep 13 20:00:00 FW-01 test: hello\r\n"

        # Send datagram via UDP socket
        transport, _ = await loop.create_datagram_endpoint(
            asyncio.DatagramProtocol,
            remote_addr=("127.0.0.1", test_port),
        )
        transport.sendto(test_payload)
        transport.close()

        # Wait for worker to consume
        await asyncio.sleep(0.1)

        assert len(kafka.published) == 1
        envelope = kafka.published[0]
        assert envelope.integrity.hash == compute_sha256(test_payload)

        stored = await vault.get_raw_event(
            envelope.raw_storage.bucket, envelope.raw_storage.object_key
        )
        assert stored == test_payload
    finally:
        await server.stop()
