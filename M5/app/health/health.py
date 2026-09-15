"""
Prometheus Metrics definitions and Destination Health Check services.
"""
from typing import Dict, Any
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
except ImportError:
    class DummyMetric:
        def labels(self, **kwargs): return self
        def inc(self, amount=1): pass
        def set(self, val): pass
        def observe(self, val): pass

    def Counter(*args, **kwargs): return DummyMetric()
    def Histogram(*args, **kwargs): return DummyMetric()
    def Gauge(*args, **kwargs): return DummyMetric()
    def generate_latest(): return b"# Prometheus metrics not installed\n"
    CONTENT_TYPE_LATEST = "text/plain"
from fastapi import APIRouter, Response, HTTPException
from app.connectors.base import DestinationConnector

# Prometheus Metrics Definitions
ROUTING_EVENTS_TOTAL = Counter(
    "ulpf_routing_events_total",
    "Total UES events processed by M5 Smart Router",
    ["status"]
)

POLICY_MATCHES_TOTAL = Counter(
    "ulpf_policy_matches_total",
    "Total policy rules matched",
    ["policy_id"]
)

DELIVERY_SUCCESS_TOTAL = Counter(
    "ulpf_delivery_success_total",
    "Total successful event deliveries",
    ["destination"]
)

DELIVERY_FAILURE_TOTAL = Counter(
    "ulpf_delivery_failure_total",
    "Total failed event deliveries",
    ["destination", "reason"]
)

DELIVERY_RETRIES_TOTAL = Counter(
    "ulpf_delivery_retries_total",
    "Total delivery retries executed",
    ["destination"]
)

DELIVERY_LATENCY_SECONDS = Histogram(
    "ulpf_delivery_latency_seconds",
    "Delivery latency in seconds",
    ["destination"]
)

DESTINATION_HEALTH_GAUGE = Gauge(
    "ulpf_destination_health",
    "Destination health status (1 = healthy, 0 = unhealthy)",
    ["destination"]
)

router = APIRouter(tags=["Health & Observability"])


class HealthService:
    """
    Manages health checks for destination connectors pool.
    """

    def __init__(self):
        self.connectors: Dict[str, DestinationConnector] = {}

    def register_connector(self, connector: DestinationConnector) -> None:
        self.connectors[connector.name()] = connector

    async def get_all_health(self) -> Dict[str, Any]:
        health_status = {}
        all_healthy = True
        for name, connector in self.connectors.items():
            is_healthy = await connector.health()
            health_status[name] = "healthy" if is_healthy else "unhealthy"
            DESTINATION_HEALTH_GAUGE.labels(destination=name).set(1 if is_healthy else 0)
            if not is_healthy:
                all_healthy = False
        return {
            "status": "healthy" if all_healthy else "degraded",
            "destinations": health_status
        }

    async def get_destination_health(self, dest_id: str) -> Dict[str, Any]:
        if dest_id not in self.connectors:
            raise HTTPException(status_code=404, detail=f"Destination connector '{dest_id}' not found")
        connector = self.connectors[dest_id]
        is_healthy = await connector.health()
        return {
            "destination": dest_id,
            "status": "healthy" if is_healthy else "unhealthy"
        }


health_service = HealthService()


@router.get("/health")
async def health_check():
    """
    Service health endpoint.
    """
    return {"status": "ok", "module": "m5-integration", "ues_version": "1.0.0"}


@router.get("/ready")
async def readiness_check():
    """
    Readiness probe checking destination connectors health.
    """
    health = await health_service.get_all_health()
    if health["status"] == "degraded":
        return Response(content="Service Degraded", status_code=503)
    return {"status": "ready", "details": health}


@router.get("/v1/destinations")
async def list_destinations():
    """
    List all registered destination connectors and their status.
    """
    return await health_service.get_all_health()


@router.get("/v1/destinations/{id}/health")
async def destination_health(id: str):
    """
    Get health status of a specific destination connector.
    """
    return await health_service.get_destination_health(id)


@router.get("/metrics")
async def metrics():
    """
    Expose Prometheus metrics.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
