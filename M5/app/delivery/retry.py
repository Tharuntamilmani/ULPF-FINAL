"""
Reliable delivery engine with exponential backoff retries and DLQ failover.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional
from app.connectors.base import DestinationConnector
from app.delivery.ack import AckTracker
from app.delivery.dlq import DeadLetterQueue
from app.router.evaluator import extract_field_value

logger = logging.getLogger(__name__)


class RetryEngine:
    """
    Retry Engine executes delivery to destination connectors using exponential backoff,
    records acknowledgements, and promotes failed events to DLQ on max retries.
    """

    def __init__(
        self,
        max_retries: int = 3,
        initial_backoff_sec: float = 0.05,
        max_backoff_sec: float = 0.5,
        ack_tracker: Optional[AckTracker] = None,
        dlq: Optional[DeadLetterQueue] = None
    ):
        self.max_retries = max_retries
        self.initial_backoff_sec = initial_backoff_sec
        self.max_backoff_sec = max_backoff_sec
        self.ack_tracker = ack_tracker or AckTracker()
        self.dlq = dlq or DeadLetterQueue()

    async def deliver_to_connector(
        self,
        connector: DestinationConnector,
        event: Dict[str, Any]
    ) -> bool:
        """
        Deliver event to a single connector with exponential backoff retry logic.
        Returns True if acknowledged, False if routed to DLQ.
        """
        event_id = str(extract_field_value(event, "event.id") or event.get("event_id") or event.get("id") or "unknown")
        dest_name = connector.name()

        backoff = self.initial_backoff_sec
        last_error_msg = ""

        # Import metrics safely
        try:
            from app.health.health import DELIVERY_RETRIES_TOTAL, DELIVERY_LATENCY_SECONDS
        except ImportError:
            DELIVERY_RETRIES_TOTAL = None
            DELIVERY_LATENCY_SECONDS = None

        import time

        for attempt in range(1, self.max_retries + 1):
            if attempt > 1 and DELIVERY_RETRIES_TOTAL:
                DELIVERY_RETRIES_TOTAL.labels(destination=dest_name).inc()

            self.ack_tracker.record_attempt(event_id, dest_name)
            start_time = time.perf_counter()
            try:
                await connector.send(event)
                duration = time.perf_counter() - start_time
                if DELIVERY_LATENCY_SECONDS:
                    DELIVERY_LATENCY_SECONDS.labels(destination=dest_name).observe(duration)

                self.ack_tracker.record_ack(event_id, dest_name)
                logger.info(
                    f"[Delivery Engine] Successfully delivered event {event_id} to '{dest_name}' "
                    f"(attempt={attempt}, latency={duration:.4f}s, status=ACKNOWLEDGED)"
                )
                return True
            except ValueError as ve:
                duration = time.perf_counter() - start_time
                if DELIVERY_LATENCY_SECONDS:
                    DELIVERY_LATENCY_SECONDS.labels(destination=dest_name).observe(duration)

                # Permanent failure (e.g. invalid event schema/payload) -> directly route to DLQ
                last_error_msg = str(ve)
                logger.warning(
                    f"[Delivery Engine] Permanent delivery failure to '{dest_name}' for event {event_id}: {ve} "
                    f"(attempt={attempt}, latency={duration:.4f}s, failure_code=PERMANENT_SCHEMA_ERROR)"
                )
                self.ack_tracker.record_failure(event_id, dest_name, last_error_msg, is_dlq=True)
                await self.dlq.push(
                    event=event,
                    destination=dest_name,
                    attempts=attempt,
                    failure_code="PERMANENT_SCHEMA_ERROR",
                    error_message=last_error_msg
                )
                return False
            except Exception as e:
                duration = time.perf_counter() - start_time
                if DELIVERY_LATENCY_SECONDS:
                    DELIVERY_LATENCY_SECONDS.labels(destination=dest_name).observe(duration)

                # Transient failure -> exponential backoff retry
                last_error_msg = str(e)
                logger.warning(
                    f"[Delivery Engine] Attempt {attempt}/{self.max_retries} failed for event {event_id} to '{dest_name}': {e} "
                    f"(latency={duration:.4f}s, failure_code=TRANSIENT_ERROR)"
                )
                self.ack_tracker.record_failure(event_id, dest_name, last_error_msg, is_dlq=False)

                if attempt < self.max_retries:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, self.max_backoff_sec)

        # Max retries exhausted -> promote to DLQ
        self.ack_tracker.record_failure(event_id, dest_name, last_error_msg, is_dlq=True)
        await self.dlq.push(
            event=event,
            destination=dest_name,
            attempts=self.max_retries,
            failure_code="DESTINATION_UNAVAILABLE",
            error_message=f"Exhausted {self.max_retries} retries. Last error: {last_error_msg}"
        )
        return False

    async def deliver_to_all(
        self,
        connectors: List[DestinationConnector],
        event: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Deliver event concurrently across multiple connectors.
        Returns mapping of connector_name -> success boolean.
        """
        tasks = [self.deliver_to_connector(c, event) for c in connectors]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return {connectors[i].name(): results[i] for i in range(len(connectors))}
