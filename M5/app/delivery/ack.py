"""
Delivery acknowledgement tracking engine.
"""
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel


class DeliveryState(str, Enum):
    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RETRIABLE_FAILURE = "RETRIABLE_FAILURE"
    DLQ_PROMOTED = "DLQ_PROMOTED"


class DeliveryStatus(BaseModel):
    event_id: str
    destination: str
    status: DeliveryState
    attempts: int = 0
    last_error: Optional[str] = None


class AckTracker:
    """
    Tracks acknowledgement state per event and target destination.
    """

    def __init__(self):
        self.records: Dict[str, DeliveryStatus] = {}

    def _key(self, event_id: str, destination: str) -> str:
        return f"{event_id}::{destination}"

    def record_attempt(self, event_id: str, destination: str) -> DeliveryStatus:
        key = self._key(event_id, destination)
        if key not in self.records:
            self.records[key] = DeliveryStatus(
                event_id=event_id,
                destination=destination,
                status=DeliveryState.PENDING,
                attempts=1
            )
        else:
            self.records[key].attempts += 1
        return self.records[key]

    def record_ack(self, event_id: str, destination: str) -> DeliveryStatus:
        key = self._key(event_id, destination)
        status = self.records.get(key) or DeliveryStatus(
            event_id=event_id,
            destination=destination,
            status=DeliveryState.ACKNOWLEDGED,
            attempts=1
        )
        status.status = DeliveryState.ACKNOWLEDGED
        self.records[key] = status
        return status

    def record_failure(self, event_id: str, destination: str, error: str, is_dlq: bool = False) -> DeliveryStatus:
        key = self._key(event_id, destination)
        status = self.records.get(key) or DeliveryStatus(
            event_id=event_id,
            destination=destination,
            status=DeliveryState.RETRIABLE_FAILURE,
            attempts=1
        )
        status.status = DeliveryState.DLQ_PROMOTED if is_dlq else DeliveryState.RETRIABLE_FAILURE
        status.last_error = error
        self.records[key] = status
        return status

    def get_status(self, event_id: str, destination: str) -> Optional[DeliveryStatus]:
        return self.records.get(self._key(event_id, destination))
