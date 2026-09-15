"""
M2 -> M3 Adapter: M2M3Adapter.

Adapts M2 ParsedEvent to M3 ParsedEvent input structure.

Preserves:
  raw_event_id
  tenant_id
  source_id
  schema_version
  parser identity (id, name, version, confidence)
  fields
  classification (format, vendor, product, confidence)
  sha256 (authoritative raw hash)
  raw_reference (storage URI/key)

Maps flat integrity and storage fields into M3's nested structure:
  integrity.hash.algorithm = "sha256"
  integrity.hash.value = sha256
  raw.storage_ref = raw_reference
  raw.format = classification.format

Maintains structural compatibility only — does not normalize semantic fields.
"""

from typing import Dict, Any, Optional
import json
from integration.contracts.tenant_context import TenantContext


class M2M3Adapter:
    """
    Adapts M2 ParsedEvent structure into M3 ParsedEvent contract.
    Preserves tenant_id and original raw SHA-256 digest.
    """

    @classmethod
    def adapt(
        cls,
        m2_output: Any,
        tenant_context: Optional[TenantContext] = None
    ) -> Dict[str, Any]:
        if isinstance(m2_output, str):
            data = json.loads(m2_output)
        elif hasattr(m2_output, "model_dump"):
            data = m2_output.model_dump()
        elif hasattr(m2_output, "dict"):
            data = m2_output.dict()
        elif isinstance(m2_output, dict):
            data = dict(m2_output)
        else:
            raise TypeError(f"Unsupported M2 output type: {type(m2_output)}")

        raw_event_id = data.get("raw_event_id")
        if not raw_event_id:
            raise ValueError("M2 event missing mandatory 'raw_event_id'")

        # Tenant context: prioritized from trusted context, then payload
        tenant_id = (
            (tenant_context.tenant_id if tenant_context else None)
            or data.get("tenant_id")
            or "tenant-default"
        )
        source_id = (
            (tenant_context.source_id if tenant_context else None)
            or data.get("source_id")
        )

        # Classification extraction
        classification = data.get("classification") or {}
        if hasattr(classification, "model_dump"):
            classification = classification.model_dump()

        # Parser extraction
        parser = data.get("parser") or {}
        if hasattr(parser, "model_dump"):
            parser = parser.model_dump()

        # Extracted fields and unmapped fields
        fields = data.get("fields", {})
        unmapped_fields = data.get("unmapped_fields", [])

        # Map flat sha256 to nested M3 integrity structure
        sha256 = data.get("sha256")
        integrity_block: Optional[Dict[str, Any]] = None
        if sha256:
            integrity_block = {
                "hash": {
                    "algorithm": "SHA-256",
                    "value": sha256,
                },
                "raw_hash": sha256,
            }

        # Map flat raw_reference to nested M3 raw structure
        raw_reference = data.get("raw_reference")
        raw_block: Optional[Dict[str, Any]] = None
        if raw_reference or raw_event_id:
            raw_block = {
                "format": classification.get("format", "syslog"),
                "storage_ref": raw_reference,
                "raw_event_id": raw_event_id,
            }

        # Return M3 ParsedEvent compatible dictionary
        adapted: Dict[str, Any] = {
            "schema_version": data.get("schema_version", "1.0.0"),
            "raw_event_id": raw_event_id,
            "tenant_id": tenant_id,
            "source_id": source_id,
            "classification": {
                "format": classification.get("format"),
                "vendor": classification.get("vendor"),
                "product": classification.get("product"),
                "confidence": classification.get("confidence", 1.0),
            },
            "parser": {
                "id": parser.get("id"),
                "name": parser.get("name"),
                "version": parser.get("version"),
                "confidence": parser.get("confidence", 1.0),
            },
            "fields": fields,
            "unmapped_fields": unmapped_fields,
            "integrity": integrity_block,
            "raw": raw_block,
        }

        return adapted
