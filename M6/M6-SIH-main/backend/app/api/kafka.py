"""
Kafka management interface (M6 control only).
M6 may inspect/create topics and check broker health.
M6 does NOT consume event topics (ulpf.raw, ulpf.parsed, etc.).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from backend.app.core.rbac import ADMIN, require_roles
from backend.app.integrations.kafka_client import TOPICS, get_kafka_producer

router = APIRouter(prefix="/kafka")


@router.get("/topics")
async def list_topics(
    current_user: Annotated[object, Depends(require_roles(ADMIN))],
) -> dict[str, Any]:
    """List Kafka topics visible to M6."""
    producer = await get_kafka_producer()
    if producer is None:
        return {"available": False, "reason": "Kafka disabled", "topics": []}
    topics = await producer.list_topics()
    return {
        "available": True,
        "topics": topics,
        "ulpf_topics": TOPICS,
    }


@router.post("/topics/provision")
async def provision_ulpf_topics(
    current_user: Annotated[object, Depends(require_roles(ADMIN))],
) -> dict[str, Any]:
    """Create all standard ULPF Kafka topics if they don't exist."""
    producer = await get_kafka_producer()
    if producer is None:
        return {"available": False, "reason": "Kafka disabled or unavailable"}
    results = await producer.create_topics(list(TOPICS.values()))
    return {"results": results}


@router.get("/health")
async def kafka_health(
    current_user: Annotated[object, Depends(require_roles(ADMIN))],
) -> dict[str, Any]:
    """Check Kafka broker connectivity."""
    from backend.app.integrations.health_client import check_kafka

    result = await check_kafka()
    return dict[str, Any](result.as_dict())
