"""
Dead-Letter Queue (DLQ) Handler for unrecoverable delivery failures.
"""
import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from app.router.evaluator import extract_field_value

logger = logging.getLogger(__name__)


class DLQRecord(BaseModel):
    event_id: str
    destination: str
    attempts: int
    failure_code: str
    error_message: str
    failed_at: str
    event: Dict[str, Any]


class DeadLetterQueue:
    """
    Dead-Letter Queue handler storing failed events to ulpf.delivery.dlq topic or disk storage.
    """

    def __init__(
        self,
        dlq_dir: Optional[str] = None,
        topic: str = "ulpf.delivery.dlq"
    ):
        self.dlq_dir = dlq_dir or os.getenv("DLQ_LOCAL_PATH", "./data/dlq")
        self.topic = topic
        os.makedirs(self.dlq_dir, exist_ok=True)
        self.dlq_records: List[DLQRecord] = []

    async def push(
        self,
        event: Dict[str, Any],
        destination: str,
        attempts: int,
        failure_code: str,
        error_message: str
    ) -> DLQRecord:
        """
        Record a failed event into the Dead-Letter Queue without losing the original UES event.
        """
        event_id = str(extract_field_value(event, "event.id") or event.get("event_id") or event.get("id") or "unknown")

        record = DLQRecord(
            event_id=event_id,
            destination=destination,
            attempts=attempts,
            failure_code=failure_code,
            error_message=error_message,
            failed_at=datetime.now(timezone.utc).isoformat(),
            event=event
        )

        self.dlq_records.append(record)

        # Write to local DLQ file
        file_path = os.path.join(self.dlq_dir, "dlq_events.jsonl")
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")

        logger.error(f"[DLQ] Promoted event {event_id} (destination '{destination}') to DLQ after {attempts} attempts. Reason: {failure_code} - {error_message}")
        return record

    def get_records(self) -> List[DLQRecord]:
        return self.dlq_records
