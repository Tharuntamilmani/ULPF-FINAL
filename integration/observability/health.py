"""
System Health Aggregator for ULPF.
Probes health and readiness of all six modules (M1-M6) and the Integration Layer.
Never fabricates health; reports real status.
"""

import os
from typing import Dict, Any, Optional
import httpx
from pydantic import BaseModel
from fastapi import FastAPI, Response, status


class ModuleHealthStatus(BaseModel):
    module: str
    healthy: bool
    status_code: Optional[int] = None
    latency_ms: float = 0.0
    details: Dict[str, Any] = {}
    error: Optional[str] = None


class SystemHealthReport(BaseModel):
    status: str  # "HEALTHY", "DEGRADED", "UNAVAILABLE"
    modules: Dict[str, ModuleHealthStatus]
    timestamp: str


class HealthAggregator:
    """
    Collects live health telemetry from all ULPF services.
    """

    def __init__(
        self,
        m1_url: Optional[str] = None,
        m2_url: Optional[str] = None,
        m3_url: Optional[str] = None,
        m4_url: Optional[str] = None,
        m5_url: Optional[str] = None,
        m6_url: Optional[str] = None,
        gateway_url: Optional[str] = None,
        config_sync_url: Optional[str] = None,
    ):
        m1 = m1_url or os.getenv("M1_URL", "http://localhost:8001")
        m2 = m2_url or os.getenv("M2_URL", "http://localhost:8082")
        m3 = m3_url or os.getenv("M3_URL", "http://localhost:8083")
        m4 = m4_url or os.getenv("M4_URL", "http://localhost:8004")
        m5 = m5_url or os.getenv("M5_URL", "http://localhost:8085")
        m6 = m6_url or os.getenv("M6_URL", "http://localhost:8086")
        gw = gateway_url or os.getenv("GATEWAY_URL", "http://localhost:8080")
        cs = config_sync_url or os.getenv("CONFIG_SYNC_URL", "http://localhost:8081")

        self.endpoints = {
            "M1": f"{m1.rstrip('/')}/health",
            "M2": f"{m2.rstrip('/')}/health",
            "M3": f"{m3.rstrip('/')}/health",
            "M4": f"{m4.rstrip('/')}/health",
            "M5": f"{m5.rstrip('/')}/health",
            "M6": f"{m6.rstrip('/')}/health",
            "Ingress_Gateway": f"{gw.rstrip('/')}/health",
            "Config_Sync": f"{cs.rstrip('/')}/health",
        }

    async def probe_service(self, name: str, url: str) -> ModuleHealthStatus:
        import time
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url)
                latency = (time.perf_counter() - start) * 1000
                healthy = (resp.status_code in (200, 202))
                details = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                return ModuleHealthStatus(
                    module=name,
                    healthy=healthy,
                    status_code=resp.status_code,
                    latency_ms=round(latency, 2),
                    details=details,
                )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return ModuleHealthStatus(
                module=name,
                healthy=False,
                latency_ms=round(latency, 2),
                error=str(e),
            )

    async def check_system_health(self) -> SystemHealthReport:
        import asyncio
        from datetime import datetime, timezone

        # Dynamically refresh endpoints from env if instantiated earlier
        m1 = os.getenv("M1_URL", "http://localhost:8001")
        m2 = os.getenv("M2_URL", "http://localhost:8082")
        m3 = os.getenv("M3_URL", "http://localhost:8083")
        m4 = os.getenv("M4_URL", "http://localhost:8004")
        m5 = os.getenv("M5_URL", "http://localhost:8085")
        m6 = os.getenv("M6_URL", "http://localhost:8086")
        gw = os.getenv("GATEWAY_URL", "http://localhost:8080")
        cs = os.getenv("CONFIG_SYNC_URL", "http://localhost:8081")

        endpoints = {
            "M1": f"{m1.rstrip('/')}/health",
            "M2": f"{m2.rstrip('/')}/health",
            "M3": f"{m3.rstrip('/')}/health",
            "M4": f"{m4.rstrip('/')}/health",
            "M5": f"{m5.rstrip('/')}/health",
            "M6": f"{m6.rstrip('/')}/health",
            "Ingress_Gateway": f"{gw.rstrip('/')}/health",
            "Config_Sync": f"{cs.rstrip('/')}/health",
        }

        tasks = [self.probe_service(name, url) for name, url in endpoints.items()]
        results = await asyncio.gather(*tasks)

        module_map = {res.module: res for res in results}
        all_healthy = all(res.healthy for res in results)
        core_healthy = all(
            module_map[mod].healthy
            for mod in ["M1", "M2", "M3", "M4", "M5", "M6"]
            if mod in module_map
        )

        overall_status = "HEALTHY" if all_healthy else ("DEGRADED" if core_healthy else "UNAVAILABLE")

        return SystemHealthReport(
            status=overall_status,
            modules=module_map,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


health_app = FastAPI(title="ULPF System Health Aggregator", version="1.0.0")
aggregator_instance = HealthAggregator()


@health_app.get("/live")
async def live():
    return {"status": "ok", "service": "health-aggregator"}


@health_app.get("/health", response_model=SystemHealthReport)
async def get_system_health(response: Response):
    report = await aggregator_instance.check_system_health()
    if report.status == "UNAVAILABLE":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif report.status == "DEGRADED":
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_200_OK
    return report
