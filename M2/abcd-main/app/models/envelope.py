import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, model_validator


def _empty_metadata_dict() -> Dict[str, Any]:
    return {}


class RawEventEnvelope(BaseModel):
    """Frozen M1 Inbound Ingestion Contract Envelope."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "schema_version": "1.0.0",
                "raw_event_id": "raw_01JXYZ789",
                "tenant_id": "tenant-default",
                "source_id": "src-cisco-asa-01",
                "received_at": "2026-09-12T04:00:15.123Z",
                "transport": "syslog",
                "payload": "<189>Sep 12 04:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443",
                "encoding": "utf-8",
                "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "raw_reference": "s3://raw-logs/tenant-default/2026/09/12/raw_01JXYZ789.log",
                "source_ip": "192.168.1.1",
                "metadata": {"facility": 23, "severity": 5},
            }
        },
    )

    schema_version: str = Field("1.0.0", description="Contract schema version from M1")
    raw_event_id: str = Field(
        ..., description="Unique identifier for raw event assigned by M1"
    )
    tenant_id: str = Field(
        "tenant-default", description="Tenant identifier for multi-tenant isolation"
    )
    source_id: Optional[str] = Field(
        None, description="Identifier for collector or emitting source device"
    )
    received_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO8601 timestamp when event was ingested by M1",
    )
    transport: str = Field(
        "syslog",
        description="Ingestion transport protocol: syslog, http, kafka, tcp, udp, tls",
    )
    payload: str = Field(..., description="Raw untouched log text/string payload")
    encoding: str = Field("utf-8", description="Payload encoding format")
    sha256: Optional[str] = Field(
        None, description="SHA-256 cryptographic digest of the raw payload"
    )
    raw_reference: Optional[str] = Field(
        None, description="URI or object reference to raw blob in cold storage"
    )
    source_ip: Optional[str] = Field(
        None, description="IP address of source device or collector"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=_empty_metadata_dict, description="Metadata key-values from M1"
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_inbound(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Support legacy field 'protocol' by mapping to 'transport'
            if "protocol" in data and "transport" not in data:
                data["transport"] = data.pop("protocol")
            # Default tenant_id if missing in legacy payloads
            if "tenant_id" not in data or not data["tenant_id"]:
                data["tenant_id"] = "tenant-default"
        return data

    @model_validator(mode="after")
    def _compute_sha256_if_missing(self) -> "RawEventEnvelope":
        if not self.sha256 and self.payload is not None:
            self.sha256 = hashlib.sha256(
                self.payload.encode("utf-8", errors="replace")
            ).hexdigest()
        return self

    @property
    def protocol(self) -> str:
        """Backward compatibility alias for transport."""
        return self.transport
