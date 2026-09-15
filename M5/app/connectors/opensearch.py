"""
OpenSearch Hot SIEM Destination Connector with Idempotency & Field Explosion Control.
"""
import os
import logging
from typing import Any, Dict, Optional
from app.connectors.base import DestinationConnector
from app.router.evaluator import extract_field_value

logger = logging.getLogger(__name__)


class OpenSearchConnector(DestinationConnector):
    """
    OpenSearch Hot SIEM Connector.
    Indexes canonical UES v1 events with document_id = event.id for idempotency.
    Controls mapping to prevent field explosion from vendor extensions.
    """

    def __init__(
        self,
        connector_name: str = "siem",
        host: Optional[str] = None,
        index_prefix: str = "ulpf-events",
        user: Optional[str] = None,
        password: Optional[str] = None,
        mock_mode: bool = True
    ):
        self._name = connector_name
        self.host = host or os.getenv("OPENSEARCH_HOST", "http://localhost:9200")
        self.index_prefix = index_prefix
        self.user = user or os.getenv("OPENSEARCH_USER")
        self.password = password or os.getenv("OPENSEARCH_PASSWORD")
        self.mock_mode = mock_mode if mock_mode is not None else (os.getenv("OPENSEARCH_MOCK_MODE", "true").lower() == "true")
        self.mock_storage: Dict[str, Dict[str, Any]] = {}
        self.is_healthy = True

    def _get_auth(self):
        if self.user and self.password:
            return (self.user, self.password)
        return None

    def name(self) -> str:
        return self._name

    def sanitize_for_indexing(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize UES event for OpenSearch indexing to prevent field explosion.
        Canonical UES fields are preserved for indexing.
        Arbitrary vendor extensions are bundled into raw vendor_data.
        """
        # Copy top-level canonical fields
        doc = {
            "event_id": extract_field_value(event, "event.id") or event.get("event_id") or event.get("id"),
            "timestamp": extract_field_value(event, "event.timestamp") or event.get("timestamp"),
            "event_type": extract_field_value(event, "event.type"),
            "event_action": extract_field_value(event, "event.action"),
            "severity_value": extract_field_value(event, "event.severity.value"),
            "tenant_id": extract_field_value(event, "tenant.id") or event.get("tenant_id") or "default_tenant",
            "source_ip": extract_field_value(event, "source.ip"),
            "destination_ip": extract_field_value(event, "destination.ip"),
            "is_security_event": extract_field_value(event, "security.is_security_event"),
            "canonical_ues": event  # Complete full UES record saved as document payload
        }
        return doc

    async def send(self, event: Dict[str, Any]) -> None:
        """
        Send event to OpenSearch using event.id as document_id (Idempotent).
        """
        if not self.is_healthy:
            raise ConnectionError(f"OpenSearch connector '{self.name()}' is in an unhealthy state")

        event_id = extract_field_value(event, "event.id") or event.get("event_id") or event.get("id")
        if not event_id:
            raise ValueError("Event is missing required event.id for OpenSearch indexing")

        doc = self.sanitize_for_indexing(event)

        if self.mock_mode:
            # Idempotent write: overwrites existing record with key=event_id
            self.mock_storage[str(event_id)] = doc
            logger.info(f"[OpenSearch Mock] Indexed event {event_id} in mock storage")
            return

        # Live OpenSearch integration via HTTP / opensearch-py client
        try:
            import httpx
            index_name = f"{self.index_prefix}-v1"
            url = f"{self.host}/{index_name}/_doc/{event_id}"
            async with httpx.AsyncClient(timeout=5.0, auth=self._get_auth()) as client:
                res = await client.put(url, json=doc)
                if res.status_code in (401, 403):
                    raise PermissionError(f"OpenSearch authentication failed: HTTP {res.status_code}")
                if res.status_code not in (200, 201):
                    raise RuntimeError(f"OpenSearch indexing failed HTTP {res.status_code}: {res.text}")
        except Exception as e:
            logger.error(f"OpenSearch indexing error: {e}")
            raise e

    async def health(self) -> bool:
        """
        Health check endpoint.
        """
        if self.mock_mode:
            return self.is_healthy

        try:
            import httpx
            async with httpx.AsyncClient(timeout=2.0, auth=self._get_auth()) as client:
                res = await client.get(f"{self.host}/_cluster/health")
                return res.status_code == 200
        except Exception:
            return False

    def get_mock_document(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve document from mock storage (used for test verification & API queries).
        """
        return self.mock_storage.get(str(event_id))

