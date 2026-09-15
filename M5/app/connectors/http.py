"""
HTTP Webhook Destination Connector for external REST/API consumers.
"""
import os
import logging
from typing import Any, Dict, List, Optional
from app.connectors.base import DestinationConnector
from app.router.evaluator import extract_field_value

logger = logging.getLogger(__name__)


class HttpConnector(DestinationConnector):
    """
    HTTP Webhook Connector for pushing events to external REST endpoints.
    """

    def __init__(
        self,
        connector_name: str = "http_webhook",
        target_url: Optional[str] = None,
        timeout_sec: float = 5.0,
        mock_mode: bool = True
    ):
        self._name = connector_name
        self.target_url = target_url or os.getenv("HTTP_WEBHOOK_URL", "http://localhost:9090/webhook")
        self.timeout_sec = timeout_sec
        self.mock_mode = mock_mode if mock_mode is not None else (os.getenv("HTTP_MOCK_MODE", "true").lower() == "true")
        self.sent_events: List[Dict[str, Any]] = []
        self.is_healthy = True

    def name(self) -> str:
        return self._name

    async def send(self, event: Dict[str, Any]) -> None:
        """
        POST event to target HTTP endpoint.
        """
        if not self.is_healthy:
            raise ConnectionError(f"HTTP connector '{self.name()}' is in an unhealthy state")

        event_id = extract_field_value(event, "event.id") or event.get("event_id") or event.get("id")

        if self.mock_mode:
            self.sent_events.append(event)
            logger.info(f"[HTTP Mock] POST event {event_id} to {self.target_url}")
            return

        try:
            import httpx
            tenant_id = extract_field_value(event, "tenant.id") or event.get("tenant_id") or ""
            headers = {
                "Content-Type": "application/json",
                "X-ULPF-Event-ID": str(event_id),
                "X-Tenant-ID": str(tenant_id)
            }
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                res = await client.post(self.target_url, json=event, headers=headers)
                if res.status_code not in (200, 201, 202, 204):
                    raise RuntimeError(f"HTTP POST delivery failed ({res.status_code}): {res.text}")
        except Exception as e:
            logger.error(f"HTTP connector delivery failure to {self.target_url}: {e}")
            raise e

    async def health(self) -> bool:
        """
        Health check endpoint.
        """
        return self.is_healthy
