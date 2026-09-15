"""
Traceability and hop tracking context across ULPF integration layer.
Logs and tracks each stage:
  M1 Ingestion -> M2 Parser -> M3 Normalizer -> M4 Enrichment -> M5 Routing
"""

import time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class HopRecord(BaseModel):
    module: str
    action: str
    status: str
    timestamp_ms: float = Field(default_factory=lambda: time.time() * 1000)
    details: Dict[str, Any] = Field(default_factory=dict)


class TraceContext(BaseModel):
    correlation_id: str
    raw_event_id: Optional[str] = None
    event_id: Optional[str] = None
    tenant_id: Optional[str] = None
    source_id: Optional[str] = None
    hops: List[HopRecord] = Field(default_factory=list)

    def record_hop(self, module: str, action: str, status: str, **details) -> None:
        self.hops.append(
            HopRecord(
                module=module,
                action=action,
                status=status,
                details=details
            )
        )

    def to_diagnostics(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "raw_event_id": self.raw_event_id,
            "event_id": self.event_id,
            "tenant_id": self.tenant_id,
            "source_id": self.source_id,
            "hop_count": len(self.hops),
            "hops": [h.model_dump() for h in self.hops],
        }
