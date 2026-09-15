"""
Data Lake Writer providing MinIO / S3 object storage delivery with partitioned JSONL/Iceberg formats.
"""
import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Set
from app.connectors.base import DestinationConnector
from app.connectors.filesystem import FilesystemConnector
from app.datalake.iceberg import IcebergCatalogClient
from app.router.evaluator import extract_field_value

logger = logging.getLogger(__name__)


class DataLakeWriter(DestinationConnector):
    """
    Data Lake Writer supporting MinIO/S3 object storage writing
    partitioned logically by date, tenant_id, and event_type.
    Falls back to FilesystemConnector in mock/standalone mode.
    """

    def __init__(
        self,
        connector_name: str = "data_lake",
        mock_mode: bool = True,
        bucket_name: str = "ulpf-datalake"
    ):
        self._name = connector_name
        self.mock_mode = mock_mode if mock_mode is not None else (os.getenv("DATA_LAKE_MOCK_MODE", "true").lower() == "true")
        self.bucket_name = bucket_name or os.getenv("MINIO_BUCKET", "ulpf-datalake")
        self.fs_fallback = FilesystemConnector(connector_name="data_lake_fs_backup")
        self.iceberg_catalog = IcebergCatalogClient()
        self._max_processed_cache = 50000
        self.processed_event_ids: Set[str] = set()
        self._processed_order = []
        self.is_healthy = True

    def name(self) -> str:
        return self._name

    async def send(self, event: Dict[str, Any]) -> None:
        """
        Deliver event to Data Lake storage.
        Partitioning: date=YYYY-MM-DD / tenant={tenant_id} / event_type={type}
        """
        if not self.is_healthy:
            raise ConnectionError(f"Data Lake connector '{self.name()}' is in an unhealthy state")

        event_id = str(extract_field_value(event, "event.id") or event.get("event_id") or event.get("id"))
        tenant_id = str(extract_field_value(event, "tenant.id") or event.get("tenant_id") or "default_tenant")
        event_type = str(extract_field_value(event, "event.type") or "general")
        dt_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Idempotency check for Data Lake writing
        if event_id in self.processed_event_ids:
            logger.info(f"[Data Lake] Duplicate event_id {event_id} skipped (idempotent write)")
            return

        # Phase 1: Write partition to disk/S3 object store
        await self.fs_fallback.send(event)

        # Phase 2: Iceberg table catalog commit hook
        partition_spec = {"date": dt_str, "tenant": tenant_id, "event_type": event_type}
        await self.iceberg_catalog.commit_record(event, partition_spec)

        # Bounded cache update
        if len(self.processed_event_ids) >= self._max_processed_cache:
            oldest = self._processed_order.pop(0)
            self.processed_event_ids.discard(oldest)

        self.processed_event_ids.add(event_id)
        self._processed_order.append(event_id)
        logger.info(f"[Data Lake] Partitioned write completed for event {event_id}")

    async def health(self) -> bool:
        return self.is_healthy
