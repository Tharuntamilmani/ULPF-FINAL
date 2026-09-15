"""Canonical UES v1 event contract for ULPF M4."""

import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.contracts.integrity_contract import IntegrityMetadata

EVENT_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]{1,128}$")


class EventMetadata(BaseModel):
    """Core event identification and classification."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique event identifier")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of the event occurrence")
    kind: str = Field(default="event", description="High-level category (event, metric, alert)")
    type: list[str] = Field(
        default_factory=lambda: ["info"], description="Event classification types"
    )
    category: list[str] = Field(default_factory=lambda: ["general"], description="Event categories")
    outcome: str = Field(default="unknown", description="Outcome (success, failure, unknown)")
    duration: int | None = Field(default=None, description="Event duration in nanoseconds")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("event.id cannot be empty")
        v_clean = v.strip()
        if not EVENT_ID_REGEX.match(v_clean):
            raise ValueError(f"Invalid event.id format: {v_clean}")
        return v_clean


class Endpoint(BaseModel):
    """Network or logical endpoint details."""

    model_config = ConfigDict(extra="forbid")

    ip: str | None = None
    port: int | None = None
    mac: str | None = None
    nat_ip: str | None = None
    domain: str | None = None
    user: str | None = None


class Network(BaseModel):
    """Network layer metadata."""

    model_config = ConfigDict(extra="forbid")

    transport: str | None = None
    protocol: str | None = None
    direction: str | None = None
    bytes_in: int | None = None
    bytes_out: int | None = None


class Observer(BaseModel):
    """Observing sensor or agent."""

    model_config = ConfigDict(extra="forbid")

    hostname: str | None = None
    ip: str | None = None
    type: str | None = None
    version: str | None = None


class Host(BaseModel):
    """Host/endpoint metadata."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    name: str | None = None
    hostname: str | None = None
    os: str | None = None
    architecture: str | None = None


class Identity(BaseModel):
    """User/Account identity metadata."""

    model_config = ConfigDict(extra="forbid")

    user_id: str | None = None
    username: str | None = None
    email: str | None = None
    domain: str | None = None
    groups: list[str] = Field(default_factory=list)


class Application(BaseModel):
    """Application metadata."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    version: str | None = None


class Process(BaseModel):
    """Process execution metadata."""

    model_config = ConfigDict(extra="forbid")

    pid: int | None = None
    name: str | None = None
    executable: str | None = None
    command_line: str | None = None


class Security(BaseModel):
    """Security classification and risk scoring."""

    model_config = ConfigDict(extra="forbid")

    severity: str = Field(default="informational")
    risk_score: float | None = None
    threat_indicator: str | None = None


class ParserMetadata(BaseModel):
    """Upstream parsing lineage."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="unknown")
    version: str = Field(default="1.0.0")
    parsed_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class NormalizationMetadata(BaseModel):
    """Upstream normalization lineage."""

    model_config = ConfigDict(extra="forbid")

    schema_target: str = Field(default="ues.v1")
    normalized_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    rule_version: str = Field(default="1.0.0")


class ProvenanceMetadata(BaseModel):
    """Upstream raw provenance."""

    model_config = ConfigDict(extra="forbid")

    raw_event_id: str = Field(..., description="Immutable identifier of raw input event")
    ingestion_timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    pipeline_id: str = Field(default="ulpf-pipeline")

    @field_validator("raw_event_id")
    @classmethod
    def validate_raw_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("provenance.raw_event_id cannot be empty")
        return v.strip()


class VendorMetadata(BaseModel):
    """Vendor source specification."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="generic")
    product: str = Field(default="generic")
    version: str | None = None


class TenantMetadata(BaseModel):
    """Tenant routing and isolation context within the canonical event."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(default="default", description="Tenant identifier")
    scope: dict[str, Any] = Field(default_factory=dict)


class CanonicalEvent(BaseModel):
    """Internal M4 Canonical UES v1 Event representation.

    All upstream truth (ids, raw provenance, timestamps, source/destination IPs)
    is strictly authoritative and MUST be preserved by M4.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(
        default="ues.v1", description="Canonical schema specification version"
    )
    event: EventMetadata
    observer: Observer = Field(default_factory=Observer)
    source: Endpoint = Field(default_factory=Endpoint)
    destination: Endpoint = Field(default_factory=Endpoint)
    network: Network = Field(default_factory=Network)
    host: Host = Field(default_factory=Host)
    identity: Identity = Field(default_factory=Identity)
    application: Application = Field(default_factory=Application)
    process: Process = Field(default_factory=Process)
    security: Security = Field(default_factory=Security)
    parser: ParserMetadata = Field(default_factory=ParserMetadata)
    normalization: NormalizationMetadata = Field(default_factory=NormalizationMetadata)
    provenance: ProvenanceMetadata
    integrity: IntegrityMetadata | None = None
    raw: str | None = None
    vendor: VendorMetadata = Field(default_factory=VendorMetadata)
    extensions: dict[str, Any] = Field(
        default_factory=dict, description="Extension namespace; enrichment data is merged here"
    )
    tenant: TenantMetadata = Field(default_factory=TenantMetadata)
