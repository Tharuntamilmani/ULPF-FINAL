"""
M5 Policy Engine + Smart Router FastAPI Main Application Entrypoint.
"""
import os
import sys
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Include module path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.policy.engine import PolicyEngine
from app.connectors.opensearch import OpenSearchConnector
from app.connectors.kafka import KafkaConnector
from app.connectors.http import HttpConnector
from app.datalake.writer import DataLakeWriter
from app.delivery.retry import RetryEngine
from app.delivery.ack import AckTracker
from app.delivery.dlq import DeadLetterQueue
from app.health.health import (
    router as health_router,
    health_service,
    ROUTING_EVENTS_TOTAL,
    POLICY_MATCHES_TOTAL,
    DELIVERY_SUCCESS_TOTAL,
    DELIVERY_FAILURE_TOTAL
)
from app.api.events import router as events_router, set_opensearch_connector
from app.api.search import router as search_router, set_policy_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("m5-app")

# Global instances
policy_engine: PolicyEngine = None
connectors_pool: Dict[str, Any] = {}
retry_engine: RetryEngine = None
ack_tracker = AckTracker()
dlq = DeadLetterQueue()


def initialize_m5_components(policy_file: Optional[str] = None):
    global policy_engine, connectors_pool, retry_engine

    policy_path = policy_file or os.getenv("POLICY_FILE_PATH", "./policies/default.yaml")
    if not os.path.isabs(policy_path):
        # Resolve relative to module root
        module_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        policy_path = os.path.join(module_root, policy_path)

    policy_engine = PolicyEngine(policy_file_path=policy_path)
    set_policy_engine(policy_engine)

    # Initialize destination connectors
    opensearch_conn = OpenSearchConnector(connector_name="siem")
    datalake_conn = DataLakeWriter(connector_name="data_lake")
    kafka_conn = KafkaConnector(connector_name="ai_stream", topic="ulpf.ai.events")
    http_conn = HttpConnector(connector_name="http_webhook")

    connectors_pool = {
        "siem": opensearch_conn,
        "data_lake": datalake_conn,
        "ai_stream": kafka_conn,
        "http_webhook": http_conn
    }

    # Register health service handles
    health_service.register_connector(opensearch_conn)
    health_service.register_connector(datalake_conn)
    health_service.register_connector(kafka_conn)
    health_service.register_connector(http_conn)

    # Register API connectors
    set_opensearch_connector(opensearch_conn)

    # Delivery retry engine
    retry_engine = RetryEngine(
        max_retries=int(os.getenv("MAX_DELIVERY_RETRIES", "3")),
        initial_backoff_sec=float(os.getenv("INITIAL_RETRY_BACKOFF_SEC", "0.05")),
        ack_tracker=ack_tracker,
        dlq=dlq
    )

    logger.info(f"M5 initialized successfully with {len(policy_engine.list_policies())} policies and {len(connectors_pool)} connectors.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_m5_components()
    yield


app = FastAPI(
    title="ULPF M5 - Policy Engine & Smart Router API",
    description="Unified Log Processing Framework Member 5 output delivery service.",
    version="1.0.0",
    lifespan=lifespan
)

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
allow_creds = False if "*" in allowed_origins else True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_creds,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(events_router)
app.include_router(search_router)


@app.post("/v1/events/process", tags=["Ingestion & Delivery Pipeline"])
async def process_event(event: Dict[str, Any] = Body(...)):
    """
    Core M5 Ingestion Endpoint:
    Receives enriched UES v1.0.0 event from M4, evaluates policy, routes to destinations,
    and executes reliable delivery with retry & DLQ guarantees.
    """
    if not policy_engine or not retry_engine:
        raise HTTPException(status_code=503, detail="M5 application component not initialized")

    # Step 0: Input validation of canonical UES structure
    if not event or not isinstance(event, dict):
        raise HTTPException(status_code=422, detail="Malformed payload: Expected JSON object")

    event_id = None
    if "event" in event and isinstance(event["event"], dict):
        event_id = event["event"].get("id")
    if not event_id:
        event_id = event.get("event_id") or event.get("id")

    if not event_id:
        raise HTTPException(status_code=422, detail="Malformed UES event: Missing required event.id")

    ROUTING_EVENTS_TOTAL.labels(status="received").inc()

    # Step 1: Smart Router policy evaluation (Preserves UES event intact!)
    destinations, decision = policy_engine.evaluate(event)

    for pol in decision.matched_policies:
        POLICY_MATCHES_TOTAL.labels(policy_id=pol).inc()

    if not destinations:
        ROUTING_EVENTS_TOTAL.labels(status="unrouted").inc()
        return {
            "status": "unrouted",
            "event_id": decision.event_id,
            "decision": decision.model_dump(),
            "delivered_destinations": []
        }

    # Step 2: Resolve connector objects for target destinations
    target_connectors = []
    for dest in destinations:
        if dest in connectors_pool:
            target_connectors.append(connectors_pool[dest])
        else:
            logger.warning(f"Destination connector '{dest}' specified by policy not found in connector pool")

    # Step 3: Execute concurrent delivery with retry and DLQ semantics
    delivery_results = await retry_engine.deliver_to_all(target_connectors, event)

    for dest, success in delivery_results.items():
        if success:
            DELIVERY_SUCCESS_TOTAL.labels(destination=dest).inc()
        else:
            DELIVERY_FAILURE_TOTAL.labels(destination=dest, reason="max_retries_or_error").inc()

    # Enrich decision audit with per-destination execution state
    status_breakdown = {}
    for conn in target_connectors:
        st = ack_tracker.get_status(decision.event_id, conn.name())
        if st:
            status_breakdown[conn.name()] = st.model_dump()
    decision.delivery_status = status_breakdown

    ROUTING_EVENTS_TOTAL.labels(status="delivered").inc()

    return {
        "status": "processed",
        "event_id": decision.event_id,
        "decision": decision.model_dump(),
        "delivery_results": delivery_results
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8085))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
