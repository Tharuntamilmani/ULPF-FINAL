"""Health, readiness, and metrics endpoints for ULPF M4."""

from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.deps import get_config_manager, get_registry
from app.config.lifecycle import ConfigurationManager
from app.observability.metrics import METRICS_REGISTRY
from app.providers.registry import ProviderRegistry

router = APIRouter(tags=["Observability"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Liveness probe returning simple health status."""
    return {"status": "healthy", "module": "M4", "version": "1.0.0"}


@router.get("/ready")
def readiness_check(
    registry: ProviderRegistry = Depends(get_registry),
    config_mgr: ConfigurationManager = Depends(get_config_manager),
) -> dict[str, object]:
    """Readiness probe checking provider availability and active configuration."""
    active_cfg = config_mgr.get_active()
    return {
        "status": "ready",
        "module": "M4",
        "providers_registered": len(registry.list_providers()),
        "active_configuration_version": active_cfg.version,
    }


@router.get("/metrics")
def prometheus_metrics() -> Response:
    """Expose Prometheus telemetry in standard text format."""
    metrics_data = generate_latest(METRICS_REGISTRY)
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
