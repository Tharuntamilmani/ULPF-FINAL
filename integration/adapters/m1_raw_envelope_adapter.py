"""
M1 -> M2 Adapter: M1RawEnvelopeAdapter.

Resolves P0-1:
M1 emits RawEventEnvelope with nested structures:
  transport.protocol
  payload.data
  payload.encoding
  integrity.hash
  raw_storage.object_key

M2 expects flattened fields:
  transport
  payload
  encoding
  sha256
  raw_reference

Preserves:
  schema_version
  raw_event_id
  tenant_id
  source_id
  received_at

Rule:
  NEVER recalculate sha256 unless explicitly necessary. The M1 raw digest is authoritative.
"""

from typing import Dict, Any, Optional
import json
from integration.contracts.tenant_context import TenantContext


class M1RawEnvelopeAdapter:
    """
    Adapts M1 RawEventEnvelope into M2 RawEventEnvelope format.
    Accepts raw dict, JSON string, or Pydantic model.
    """

    @classmethod
    def adapt(
        cls,
        raw_input: Any,
        tenant_context: Optional[TenantContext] = None
    ) -> Dict[str, Any]:
        """
        Transform M1 nested envelope to M2 flat envelope dictionary.
        """
        if isinstance(raw_input, str):
            data = json.loads(raw_input)
        elif hasattr(raw_input, "model_dump"):
            data = raw_input.model_dump()
        elif hasattr(raw_input, "dict"):
            data = raw_input.dict()
        elif isinstance(raw_input, dict):
            data = dict(raw_input)
        else:
            raise TypeError(f"Unsupported M1 input type: {type(raw_input)}")

        # 1. Payload extraction
        raw_payload = data.get("payload")
        if isinstance(raw_payload, dict):
            payload_str = raw_payload.get("data", "")
            encoding = raw_payload.get("encoding", "utf-8")
        elif isinstance(raw_payload, str):
            payload_str = raw_payload
            encoding = data.get("encoding", "utf-8")
        else:
            payload_str = str(raw_payload or "")
            encoding = data.get("encoding", "utf-8")

        # 2. Transport protocol extraction
        transport_data = data.get("transport")
        if isinstance(transport_data, dict):
            transport_str = transport_data.get("protocol") or transport_data.get("type") or "syslog"
        elif isinstance(transport_data, str):
            transport_str = transport_data
        else:
            transport_str = data.get("protocol", "syslog")

        # 3. Integrity hash extraction (Authoritative M1 raw digest)
        integrity_data = data.get("integrity")
        if isinstance(integrity_data, dict):
            sha256_hash = integrity_data.get("hash") or integrity_data.get("value")
        elif isinstance(integrity_data, str):
            sha256_hash = integrity_data
        else:
            sha256_hash = data.get("sha256")

        # 4. Storage reference extraction
        storage_data = data.get("raw_storage")
        if isinstance(storage_data, dict):
            raw_reference = (
                storage_data.get("object_key")
                or storage_data.get("uri")
                or storage_data.get("s3_uri")
            )
        elif isinstance(storage_data, str):
            raw_reference = storage_data
        else:
            raw_reference = data.get("raw_reference")

        # 5. Tenant context resolution (Preserve trusted context or payload field)
        tenant_id = (
            (tenant_context.tenant_id if tenant_context else None)
            or data.get("tenant_id")
            or "tenant-default"
        )
        source_id = (
            (tenant_context.source_id if tenant_context else None)
            or data.get("source_id")
        )

        # 6. Preserve top-level identifiers
        raw_event_id = data.get("raw_event_id")
        if not raw_event_id:
            raise ValueError("M1 envelope missing mandatory 'raw_event_id'")

        received_at = data.get("received_at") or data.get("timestamp")

        # Metadata dictionary
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        # Preserve source IP if present in transport or metadata
        source_ip = data.get("source_ip")
        if not source_ip and isinstance(transport_data, dict):
            source_ip = transport_data.get("client_ip") or transport_data.get("remote_ip")

        # Build M2-compatible flat dictionary
        adapted: Dict[str, Any] = {
            "schema_version": data.get("schema_version", "1.0.0"),
            "raw_event_id": raw_event_id,
            "tenant_id": tenant_id,
            "source_id": source_id,
            "transport": transport_str,
            "payload": payload_str,
            "encoding": encoding,
            "sha256": sha256_hash,
            "raw_reference": raw_reference,
            "source_ip": source_ip,
            "metadata": metadata,
        }

        if received_at:
            adapted["received_at"] = received_at

        return adapted
