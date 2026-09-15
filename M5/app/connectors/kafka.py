"""
Kafka Destination Connector for real-time streaming (e.g., ulpf.ai.events).
"""
import os
import json
import logging
from typing import Any, Dict, List, Optional
from app.connectors.base import DestinationConnector
from app.router.evaluator import extract_field_value

logger = logging.getLogger(__name__)


class KafkaConnector(DestinationConnector):
    """
    Kafka Destination Connector for AI/ML real-time streaming and messaging.
    """

    def __init__(
        self,
        connector_name: str = "ai_stream",
        topic: str = "ulpf.ai.events",
        bootstrap_servers: Optional[str] = None,
        mock_mode: bool = True
    ):
        self._name = connector_name
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.mock_mode = mock_mode if mock_mode is not None else (os.getenv("KAFKA_MOCK_MODE", "true").lower() == "true")
        self.mock_topics: Dict[str, List[Dict[str, Any]]] = {self.topic: []}
        self.is_healthy = True

    def name(self) -> str:
        return self._name

    async def send(self, event: Dict[str, Any]) -> None:
        """
        Produce UES event to Kafka topic.
        """
        if not self.is_healthy:
            raise ConnectionError(f"Kafka connector '{self.name()}' is in an unhealthy state")

        event_id = extract_field_value(event, "event.id") or event.get("event_id") or event.get("id")

        if self.mock_mode:
            if self.topic not in self.mock_topics:
                self.mock_topics[self.topic] = []
            self.mock_topics[self.topic].append(event)
            logger.info(f"[Kafka Mock] Published event {event_id} to topic '{self.topic}'")
            return

        try:
            from aiokafka import AIOKafkaProducer
            producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
            await producer.start()
            try:
                payload = json.dumps(event).encode("utf-8")
                key = str(event_id).encode("utf-8") if event_id else None
                await producer.send_and_wait(self.topic, value=payload, key=key)
            finally:
                await producer.stop()
        except Exception as e:
            logger.error(f"Kafka producer failure on topic '{self.topic}': {e}")
            raise e

    async def health(self) -> bool:
        """
        Health check endpoint.
        """
        return self.is_healthy

    def get_mock_events(self, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve mock stream events for tests and verification.
        """
        t = topic or self.topic
        return self.mock_topics.get(t, [])
