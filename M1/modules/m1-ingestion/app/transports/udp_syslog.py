import asyncio

import structlog

from app.config.settings import Settings
from app.health.metrics import INGEST_REJECTED_TOTAL
from app.messaging.kafka import KafkaProducerWrapper
from app.storage.outbox import DurableOutbox
from app.storage.raw_vault import RawVault
from app.transports.pipeline import process_raw_payload

logger = structlog.get_logger(__name__)


class UdpSyslogProtocol(asyncio.DatagramProtocol):
    def __init__(
        self,
        queue: "asyncio.Queue[tuple[bytes, tuple[str, int]]]",
    ):
        self.queue = queue

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        if not data:
            return
        try:
            self.queue.put_nowait((data, addr))
        except asyncio.QueueFull:
            INGEST_REJECTED_TOTAL.labels(reason="udp_queue_full").inc()
            logger.warning(
                "UDP datagram rejected: queue full",
                queue_size=self.queue.maxsize,
                client_ip=addr[0],
            )


class UdpSyslogServer:
    def __init__(
        self,
        host: str,
        port: int,
        settings: Settings,
        raw_vault: RawVault,
        kafka_producer: KafkaProducerWrapper,
        outbox: DurableOutbox | None = None,
    ):
        self.host = host
        self.port = port
        self.settings = settings
        self.raw_vault = raw_vault
        self.kafka_producer = kafka_producer
        self.outbox = outbox
        self.transport: asyncio.DatagramTransport | None = None
        self.queue: asyncio.Queue[tuple[bytes, tuple[str, int]]] = asyncio.Queue(
            maxsize=settings.udp_queue_size
        )
        self.workers: list[asyncio.Task[None]] = []
        self.num_workers = settings.udp_workers

    async def _worker(self, worker_id: int) -> None:
        logger.debug("UDP worker started", worker_id=worker_id)
        while True:
            try:
                data, addr = await self.queue.get()
            except asyncio.CancelledError:
                break

            try:
                client_ip = addr[0]
                metadata = {
                    "tenant_id": self.settings.default_tenant_id,
                    "source_id": f"syslog-udp-{client_ip}",
                    "source_type": self.settings.default_source_type,
                    "ingest_zone": self.settings.default_ingest_zone,
                    "collector_id": self.settings.default_collector_id,
                }
                await process_raw_payload(
                    raw_bytes=data,
                    metadata=metadata,
                    transport_protocol="udp",
                    transport_port=self.port,
                    raw_vault=self.raw_vault,
                    kafka_producer=self.kafka_producer,
                    format_hint="syslog",
                    bucket_name=self.settings.minio_bucket_raw,
                    outbox=self.outbox,
                )
            except asyncio.CancelledError:
                self.queue.task_done()
                break
            except Exception as e:
                logger.error("Error in UDP syslog packet processing", addr=addr, error=str(e))
            finally:
                self.queue.task_done()

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        # Start bounded worker pool
        self.workers = [
            asyncio.create_task(self._worker(i), name=f"udp-worker-{i}")
            for i in range(self.num_workers)
        ]

        transport, _ = await loop.create_datagram_endpoint(
            lambda: UdpSyslogProtocol(queue=self.queue),
            local_addr=(self.host, self.port),
        )
        self.transport = transport
        logger.info(
            "UDP Syslog listener active",
            host=self.host,
            port=self.port,
            queue_size=self.settings.udp_queue_size,
            workers=self.num_workers,
        )

    async def stop(self) -> None:
        if self.transport:
            self.transport.close()
            logger.info("UDP Syslog listener stopped")

        for worker in self.workers:
            worker.cancel()
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
            self.workers.clear()
        logger.info("UDP Syslog workers stopped")
