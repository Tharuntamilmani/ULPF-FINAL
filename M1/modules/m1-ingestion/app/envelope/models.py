from pydantic import BaseModel, Field


class TransportInfo(BaseModel):
    protocol: str = Field(..., description="Ingestion protocol (e.g. http, udp, tcp, file)")
    port: int | None = Field(None, description="Ingestion listener port")


class PayloadInfo(BaseModel):
    encoding: str = Field(default="utf-8", description="Payload encoding ('utf-8' or 'base64')")
    format_hint: str = Field(default="syslog", description="Payload hint format")
    data: str = Field(
        ..., description="Raw text payload (UTF-8 string) or base64 encoded bytes for non-UTF8"
    )


class IntegrityInfo(BaseModel):
    algorithm: str = Field(
        default="SHA-256", description="Hash algorithm used for raw bytes integrity"
    )
    hash: str = Field(..., description="SHA-256 hex digest computed over original raw bytes")


class RawStorageInfo(BaseModel):
    backend: str = Field(default="minio", description="Object storage backend type")
    bucket: str = Field(..., description="Storage bucket name")
    object_key: str = Field(..., description="Storage object key path")


class RawEventEnvelope(BaseModel):
    schema_version: str = Field(
        default="1.0.0", description="ULPF RawEventEnvelope contract version"
    )
    raw_event_id: str = Field(..., description="UUIDv7 time-sortable unique event identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    source_id: str = Field(..., description="Log source identifier")
    source_type: str = Field(default="firewall", description="Category of log source device")
    ingest_zone: str = Field(default="dmz", description="Ingestion network zone")
    collector_id: str = Field(default="collector-01", description="Ingestion collector ID")
    received_at: str = Field(..., description="ISO 8601 UTC timestamp when M1 received event")
    transport: TransportInfo
    payload: PayloadInfo
    integrity: IntegrityInfo
    raw_storage: RawStorageInfo
