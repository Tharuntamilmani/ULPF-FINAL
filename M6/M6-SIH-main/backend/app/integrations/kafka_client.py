"""
Kafka client — M6 uses Kafka only for:
  1. Publishing config-change events  (topic: ulpf.m6.config.updates)
  2. Publishing replay requests        (topic: ulpf.replay)

M6 is NOT a primary event consumer. It does not process ulpf.raw / ulpf.parsed etc.
"""

from __future__ import annotations

import json
from typing import Any

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger

logger = get_logger("kafka_client")

# Topic constants
TOPICS = {
    "raw": "ulpf.raw",
    "parsed": "ulpf.parsed",
    "normalized": "ulpf.normalized",
    "enriched": "ulpf.enriched",
    "ai_events": "ulpf.ai.events",
    "replay": "ulpf.replay",
    "parser_dlq": "ulpf.parser.dlq",
    "validation_dlq": "ulpf.validation.dlq",
    "delivery_dlq": "ulpf.delivery.dlq",
    "config_updates": "ulpf.m6.config.updates",
}


class KafkaProducer:
    """Thin async wrapper around confluent-kafka Producer."""

    def __init__(self) -> None:
        self._producer: Any = None
        self._settings = get_settings()

    async def _get_producer(self) -> Any:
        if self._producer is None:
            from confluent_kafka import Producer  # noqa: PLC0415

            config: dict[str, Any] = {
                "bootstrap.servers": self._settings.kafka_bootstrap_servers,
            }
            if self._settings.kafka_security_protocol != "PLAINTEXT":
                config["security.protocol"] = self._settings.kafka_security_protocol
            if self._settings.kafka_sasl_mechanism:
                config["sasl.mechanism"] = self._settings.kafka_sasl_mechanism
                config["sasl.username"] = self._settings.kafka_sasl_username
                config["sasl.password"] = self._settings.kafka_sasl_password
            self._producer = Producer(config)
        return self._producer

    async def publish(self, topic: str, message: str | dict[str, Any]) -> None:
        """Publish a message to a Kafka topic."""
        if isinstance(message, dict):
            message = json.dumps(message, default=str)
        try:
            producer = await self._get_producer()
            producer.produce(topic, value=message.encode("utf-8"))
            producer.poll(0)
            logger.debug("Kafka message published", topic=topic)
        except Exception as exc:
            logger.error("Kafka publish failed", topic=topic, error=str(exc))
            raise

    async def ping(self) -> bool:
        """Return True if broker is reachable."""
        try:
            from confluent_kafka.admin import AdminClient  # noqa: PLC0415

            settings = self._settings
            admin = AdminClient({"bootstrap.servers": settings.kafka_bootstrap_servers})
            metadata = admin.list_topics(timeout=3)
            return metadata is not None
        except Exception:
            return False

    async def create_topics(
        self, topics: list[str], num_partitions: int = 3, replication_factor: int = 1
    ) -> dict[str, str]:
        """Create Kafka topics if they don't exist. Returns {topic: result}."""
        from confluent_kafka.admin import AdminClient, NewTopic  # noqa: PLC0415

        settings = self._settings
        admin = AdminClient({"bootstrap.servers": settings.kafka_bootstrap_servers})
        new_topics = [
            NewTopic(t, num_partitions=num_partitions, replication_factor=replication_factor)
            for t in topics
        ]
        futures = admin.create_topics(new_topics)
        results: dict[str, str] = {}
        for topic, future in futures.items():
            try:
                future.result()
                results[topic] = "created"
            except Exception as exc:
                results[topic] = str(exc)
        return results

    async def list_topics(self) -> list[str]:
        """Return list of topic names."""
        try:
            from confluent_kafka.admin import AdminClient  # noqa: PLC0415

            admin = AdminClient({"bootstrap.servers": self._settings.kafka_bootstrap_servers})
            metadata = admin.list_topics(timeout=5)
            return list(metadata.topics.keys())
        except Exception as exc:
            logger.warning("Could not list Kafka topics", error=str(exc))
            return []


_producer: KafkaProducer | None = None


async def get_kafka_producer() -> KafkaProducer | None:
    """Return the shared producer, or None if Kafka is disabled/unavailable."""
    global _producer
    settings = get_settings()
    if not settings.kafka_enabled:
        return None
    if _producer is None:
        _producer = KafkaProducer()
    return _producer
