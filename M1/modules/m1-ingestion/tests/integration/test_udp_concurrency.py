import asyncio

import pytest

from app.config.settings import Settings
from app.health.metrics import INGEST_REJECTED_TOTAL
from app.transports.udp_syslog import UdpSyslogServer


class SlowMockRawVault:
    def __init__(self, delay_s: float = 0.05):
        self.delay_s = delay_s
        self.count = 0

    async def store_raw_event(self, bucket: str, object_key: str, payload_bytes: bytes):
        await asyncio.sleep(self.delay_s)
        self.count += 1
        return {"bucket": bucket, "object_key": object_key}

    async def is_healthy(self, bucket=None):
        return True


class SlowMockKafkaProducer:
    def __init__(self, delay_s: float = 0.2):
        self.delay_s = delay_s
        self.raw_topic = "ulpf.raw"
        self.published = []

    async def publish_envelope(self, envelope, topic=None):
        await asyncio.sleep(self.delay_s)
        self.published.append(envelope)
        return {"topic": self.raw_topic, "partition": 0, "offset": len(self.published)}

    async def is_healthy(self):
        return True


@pytest.mark.asyncio
async def test_udp_bounded_concurrency_and_overflow_rejection():
    """
    P0-6 Verification:
    Replace unbounded asyncio.create_task with bounded queue + fixed workers.
    When sink is slow, excess datagrams must be dropped, queue size must remain bounded,
    and metrics must increment for dropped datagrams.
    """
    settings = Settings()
    queue_size = 5
    num_workers = 1
    settings.udp_queue_size = queue_size
    settings.udp_workers = num_workers

    vault = SlowMockRawVault(delay_s=0.2)
    kafka = SlowMockKafkaProducer(delay_s=0.2)

    test_port = 15157
    server = UdpSyslogServer(
        host="127.0.0.1",
        port=test_port,
        settings=settings,
        raw_vault=vault,  # type: ignore
        kafka_producer=kafka,  # type: ignore
    )
    await server.start()

    # Capture initial metric value
    try:
        initial_dropped = INGEST_REJECTED_TOTAL.labels(reason="udp_queue_full")._value.get()
    except Exception:
        initial_dropped = 0.0

    try:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Blast 60 datagrams while pipeline is slow (queue is only 5)
        total_sent = 60
        for i in range(total_sent):
            sock.sendto(f"<134>burst log packet {i}\n".encode(), ("127.0.0.1", test_port))

        sock.close()

        # Allow asyncio event loop to receive datagrams from socket buffer
        await asyncio.sleep(0.05)

        # Check queue size immediately: must NEVER exceed bounded maxsize
        assert server.queue.qsize() <= queue_size
        assert len(server.workers) == num_workers

        # Wait a short moment for some processing and drops to register
        await asyncio.sleep(0.3)

        # Verify dropped metrics incremented
        current_dropped = INGEST_REJECTED_TOTAL.labels(reason="udp_queue_full")._value.get()
        dropped_count = current_dropped - initial_dropped
        assert dropped_count > 0, f"Expected drops due to queue overflow, got {dropped_count}"

        # Ensure that processed + queued + metered drops accurately reflect the burst
        processed_count = len(kafka.published)
        remaining_queued = server.queue.qsize()
        total_accounted = processed_count + remaining_queued + int(dropped_count)
        assert total_accounted >= 55, (
            f"Expected >= 55 datagrams accounted for, got {total_accounted}"
        )

    finally:
        await server.stop()
