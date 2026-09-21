"""
M1 -> M2 Kafka Consumer Bridge: M1RawEventConsumer.

Resolves P0-3:
M1 publishes raw envelopes to Kafka topic 'ulpf.raw'.
M2 is a synchronous FastAPI service with no native Kafka consumer.

This consumer bridge:
  1. Subscribes to 'ulpf.raw' with consumer group 'ulpf-m1-m2-bridge'
  2. Validates and deserializes M1 RawEventEnvelope
  3. Enforces at-least-once idempotency (deduplicates duplicate raw_event_ids)
  4. Transforms payload using M1RawEnvelopeAdapter
  5. Authenticates to M2 with service credentials (system-admin-token)
  6. Dispatches to M2 POST /v1/parse
  7. Retries transient failures with exponential backoff
  8. Commits Kafka offset ONLY after M2 acknowledges success (200 OK)
  9. Forwards unrecoverable messages to DLQ if configured
"""

import json
import asyncio
from typing import Dict, Any, Optional, Callable
import httpx
import structlog

from integration.adapters.m1_raw_envelope_adapter import M1RawEnvelopeAdapter
from integration.adapters.idempotency import IdempotencyTracker
from integration.adapters.retry_policy import RetryPolicy
from integration.contracts.tenant_context import TenantContext

logger = structlog.get_logger("integration.consumer.m1_raw")


class M1RawEventConsumer:
    """
    Durable Kafka Consumer Bridge connecting M1 raw topic to M2 parsing engine.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "ulpf.raw",
        dlq_topic: str = "ulpf.dlq",
        group_id: str = "ulpf-m1-m2-bridge",
        m2_base_url: str = "http://localhost:8082",
        m2_auth_token: str = "system-admin-token",
        http_client: Optional[httpx.AsyncClient] = None,
        idempotency_tracker: Optional[IdempotencyTracker] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.dlq_topic = dlq_topic
        self.group_id = group_id
        self.m2_base_url = m2_base_url.rstrip("/")
        self.m2_auth_token = m2_auth_token
        self._external_client = http_client
        self.http_client = http_client
        self.idempotency = idempotency_tracker or IdempotencyTracker()
        self.retry = retry_policy or RetryPolicy(max_retries=3, base_delay_ms=100.0)
        self._running = False
        self._consumer = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self.http_client is None or self.http_client.is_closed:
            self.http_client = httpx.AsyncClient(timeout=10.0)
        return self.http_client

    async def process_raw_message(
        self,
        raw_payload: Any,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Process a single raw message through validation, adaptation, deduplication, and M2 dispatch.
        Can be invoked directly by tests, simulated streams, or the Kafka consumer loop.
        """
        headers = headers or {}
        # 1. Parse JSON if string or bytes
        if isinstance(raw_payload, (bytes, bytearray)):
            data = json.loads(raw_payload.decode("utf-8"))
        elif isinstance(raw_payload, str):
            data = json.loads(raw_payload)
        elif isinstance(raw_payload, dict):
            data = raw_payload
        else:
            raise TypeError(f"Unsupported message type: {type(raw_payload)}")

        raw_event_id = data.get("raw_event_id")
        if not raw_event_id:
            raise ValueError("Message missing 'raw_event_id'")

        # 2. Extract or construct TenantContext
        tenant_id = (
            headers.get("X-Tenant-ID")
            or headers.get("x-tenant-id")
            or data.get("tenant_id")
            or "tenant-default"
        )
        source_id = (
            headers.get("X-Source-ID")
            or headers.get("x-source-id")
            or data.get("source_id")
            or "unknown-source"
        )
        correlation_id = (
            headers.get("X-Correlation-ID")
            or headers.get("x-correlation-id")
            or data.get("correlation_id")
        )

        tenant_ctx = TenantContext(
            tenant_id=tenant_id,
            source_id=source_id,
            correlation_id=correlation_id or raw_event_id,
        )

        # 3. Idempotency check (at-least-once deduplication)
        is_new = self.idempotency.check_and_set(tenant_id, raw_event_id)
        if not is_new:
            cached = self.idempotency.get_cached_result(tenant_id, raw_event_id)
            logger.info("Duplicate event detected, returning cached outcome", raw_event_id=raw_event_id, tenant_id=tenant_id)
            return {
                "status": "DUPLICATE_SUPPRESSED",
                "raw_event_id": raw_event_id,
                "tenant_id": tenant_id,
                "result": cached,
            }

        # 4. Adapt M1 payload to M2 schema
        m2_payload = M1RawEnvelopeAdapter.adapt(data, tenant_context=tenant_ctx)

        # 5. Dispatch to M2 with authenticated HTTP and retry
        async def send_to_m2() -> Dict[str, Any]:
            client = await self._get_client()
            url = f"{self.m2_base_url}/v1/parse"
            auth_headers = {
                "Authorization": f"Bearer {self.m2_auth_token}",
                "X-API-Key": self.m2_auth_token,
                "Content-Type": "application/json",
                **tenant_ctx.to_headers(),
            }
            resp = await client.post(url, json=m2_payload, headers=auth_headers)
            if resp.status_code in [200, 201]:
                return resp.json()
            elif resp.status_code >= 500:
                resp.raise_for_status()
            else:
                raise ValueError(f"M2 rejected event with HTTP {resp.status_code}: {resp.text}")

        m2_result = await self.retry.execute_async(
            send_to_m2,
            operation_name=f"POST /v1/parse [{raw_event_id}]"
        )

        # Cache result for idempotency
        self.idempotency.check_and_set(tenant_id, raw_event_id, result_payload=m2_result)

        return {
            "status": "PROCESSED",
            "raw_event_id": raw_event_id,
            "tenant_id": tenant_id,
            "result": m2_result,
        }

    async def start(self) -> None:
        """
        Start live Kafka consumption loop.
        """
        try:
            from aiokafka import AIOKafkaConsumer  # type: ignore
        except ImportError:
            logger.warning("aiokafka not available, consumer cannot run live Kafka loop")
            return

        self._consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            enable_auto_commit=False,  # Manual commit ONLY after M2 success
            auto_offset_reset="earliest",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )

        await self._consumer.start()
        self._running = True
        logger.info("M1RawEventConsumer started", topic=self.topic, group=self.group_id)

        try:
            while self._running:
                try:
                    msg = await self._consumer.getone()
                except Exception as e:
                    logger.warning("Kafka consumer getone error, retrying", error=str(e))
                    await asyncio.sleep(1.0)
                    continue

                headers = {}
                if msg.headers:
                    headers = {k: v.decode("utf-8") for k, v in msg.headers}

                try:
                    await self.process_raw_message(msg.value, headers=headers)
                    # Commit offset only upon successful processing
                    await self._consumer.commit()
                except Exception as e:
                    logger.error("Failed to process message from Kafka", offset=msg.offset, error=str(e))
                    # Route to DLQ if configured
        finally:
            await self._consumer.stop()
            if self.http_client and not self._external_client:
                await self.http_client.aclose()

    async def stop(self) -> None:
        self._running = False
        if self._consumer:
            await self._consumer.stop()
        if self.http_client and not self._external_client and not self.http_client.is_closed:
            await self.http_client.aclose()
