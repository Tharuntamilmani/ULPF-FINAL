"""
Local Filesystem Data Lake Connector for backup and standalone storage.
"""
import os
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.connectors.base import DestinationConnector
from app.router.evaluator import extract_field_value

logger = logging.getLogger(__name__)


class FilesystemConnector(DestinationConnector):
    """
    Filesystem Data Lake Connector.
    Partitioned by date=YYYY-MM-DD/tenant={tenant_id}/events.jsonl
    """

    def __init__(
        self,
        connector_name: str = "data_lake_file",
        base_dir: Optional[str] = None
    ):
        self._name = connector_name
        self.base_dir = base_dir or os.getenv("DATA_LAKE_LOCAL_PATH", "./data/datalake")
        os.makedirs(self.base_dir, exist_ok=True)
        self.is_healthy = True

    def name(self) -> str:
        return self._name

    async def send(self, event: Dict[str, Any]) -> None:
        """
        Append event as JSONL to partitioned directory on local filesystem.
        """
        if not self.is_healthy:
            raise ConnectionError(f"Filesystem connector '{self.name()}' is in an unhealthy state")

        tenant_id = extract_field_value(event, "tenant.id") or event.get("tenant_id") or "default_tenant"
        dt_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        partition_dir = os.path.join(self.base_dir, f"date={dt_str}", f"tenant={tenant_id}")
        os.makedirs(partition_dir, exist_ok=True)

        file_path = os.path.join(partition_dir, "events.jsonl")

        line = json.dumps(event, default=str) + "\n"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(line)

        logger.info(f"[Filesystem Data Lake] Written event to {file_path}")

    async def health(self) -> bool:
        return self.is_healthy
