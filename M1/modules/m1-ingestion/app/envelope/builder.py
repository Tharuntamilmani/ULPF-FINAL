from datetime import datetime, timezone
from typing import Any

from app.envelope.models import (
    IntegrityInfo,
    PayloadInfo,
    RawEventEnvelope,
    RawStorageInfo,
    TransportInfo,
)
from app.integrity.hashing import compute_sha256
from app.integrity.ids import generate_uuidv7


def generate_object_key(
    tenant_id: str,
    source_id: str,
    raw_event_id: str,
    dt: datetime | None = None,
) -> str:
    """
    Generates MinIO object key matching the standard ULPF partition layout:
    tenant={tenant_id}/year={YYYY}/month={MM}/day={DD}/source={source_id}/event={raw_event_id}
    """
    dt_utc = dt.astimezone(timezone.utc) if dt else datetime.now(timezone.utc)
    year = dt_utc.strftime("%Y")
    month = dt_utc.strftime("%m")
    day = dt_utc.strftime("%d")

    return (
        f"tenant={tenant_id}/"
        f"year={year}/"
        f"month={month}/"
        f"day={day}/"
        f"source={source_id}/"
        f"event={raw_event_id}"
    )


def build_envelope(
    raw_bytes: bytes,
    metadata: dict[str, Any],
    transport_protocol: str,
    transport_port: int | None = None,
    format_hint: str = "syslog",
    bucket_name: str = "ulpf-raw",
    received_at: datetime | None = None,
    raw_event_id: str | None = None,
) -> RawEventEnvelope:
    """
    Pure builder function for RawEventEnvelope.
    Calculates SHA-256 hash on untouched raw_bytes, generates UUIDv7 if needed,
    and constructs the downstream handoff contract.
    """
    dt_utc = received_at.astimezone(timezone.utc) if received_at else datetime.now(timezone.utc)
    timestamp_iso = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    event_id = raw_event_id or generate_uuidv7()
    sha256_hash = compute_sha256(raw_bytes)

    tenant_id = metadata.get("tenant_id", "demo-tenant")
    source_id = metadata.get("source_id", "cisco-fw-01")
    source_type = metadata.get("source_type", "firewall")
    ingest_zone = metadata.get("ingest_zone", "dmz")
    collector_id = metadata.get("collector_id", "collector-01")

    object_key = generate_object_key(
        tenant_id=tenant_id,
        source_id=source_id,
        raw_event_id=event_id,
        dt=dt_utc,
    )

    try:
        decoded_data = raw_bytes.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        import base64

        decoded_data = base64.b64encode(raw_bytes).decode("ascii")
        encoding = "base64"

    return RawEventEnvelope(
        schema_version="1.0.0",
        raw_event_id=event_id,
        tenant_id=tenant_id,
        source_id=source_id,
        source_type=source_type,
        ingest_zone=ingest_zone,
        collector_id=collector_id,
        received_at=timestamp_iso,
        transport=TransportInfo(
            protocol=transport_protocol.lower(),
            port=transport_port,
        ),
        payload=PayloadInfo(
            encoding=encoding,
            format_hint=format_hint,
            data=decoded_data,
        ),
        integrity=IntegrityInfo(
            algorithm="SHA-256",
            hash=sha256_hash,
        ),
        raw_storage=RawStorageInfo(
            backend="minio",
            bucket=bucket_name,
            object_key=object_key,
        ),
    )
