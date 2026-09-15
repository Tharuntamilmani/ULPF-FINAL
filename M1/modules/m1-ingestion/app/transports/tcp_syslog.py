import asyncio

import structlog

from app.config.settings import Settings
from app.messaging.kafka import KafkaProducerWrapper
from app.storage.outbox import DurableOutbox
from app.storage.raw_vault import RawVault
from app.transports.pipeline import process_raw_payload

logger = structlog.get_logger(__name__)


class TcpSyslogServer:
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
        self.server: asyncio.Server | None = None

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        client_ip = peer[0] if peer else "unknown"

        metadata = {
            "tenant_id": self.settings.default_tenant_id,
            "source_id": f"syslog-tcp-{client_ip}",
            "source_type": self.settings.default_source_type,
            "ingest_zone": self.settings.default_ingest_zone,
            "collector_id": self.settings.default_collector_id,
        }

        try:
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break

                await process_raw_payload(
                    raw_bytes=line,
                    metadata=metadata,
                    transport_protocol="tcp",
                    transport_port=self.port,
                    raw_vault=self.raw_vault,
                    kafka_producer=self.kafka_producer,
                    format_hint="syslog",
                    bucket_name=self.settings.minio_bucket_raw,
                    outbox=self.outbox,
                )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Error in TCP syslog stream connection", peer=peer, error=str(e))
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self) -> None:
        self.server = await asyncio.start_server(
            self._handle_client,
            host=self.host,
            port=self.port,
        )
        logger.info("TCP Syslog listener active", host=self.host, port=self.port)

    async def stop(self) -> None:
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("TCP Syslog listener stopped")
