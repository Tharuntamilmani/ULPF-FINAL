"""
M4 -> M5 Adapter: M4M5Adapter.

Resolves P1-2:
1. M4 returns EnrichmentResult wrapping {"event": ..., "integrity": ..., "provenance": ..., "diagnostics": ...}.
   M5 expects the canonical UES event dictionary directly, not the wrapper.
2. M4 emits tenant block as event["tenant"]["tenant_id"].
   M5's SmartRouter expects event["tenant"]["id"] or root event["tenant_id"].
   Without adaptation, SmartRouter.extract_tenant_id returns None, breaking tenant-scoped routing policies.
3. The adapter populates tenant.id = tenant.tenant_id while strictly preserving tenant.tenant_id.
4. Preserves M4 enriched cryptographic digest and provenance inside the event's integrity block.
"""

from typing import Dict, Any, Optional
import json


class M4M5Adapter:
    """
    Adapts M4 EnrichmentResult into M5 SmartRouter compatible event dictionary.
    """

    @classmethod
    def adapt(cls, enrichment_result: Any) -> Dict[str, Any]:
        """
        Unwrap M4 EnrichmentResult, harmonize tenant identifiers for M5,
        and attach provenance/diagnostics into event metadata.
        """
        if isinstance(enrichment_result, str):
            data = json.loads(enrichment_result)
        elif hasattr(enrichment_result, "model_dump"):
            data = enrichment_result.model_dump()
        elif hasattr(enrichment_result, "dict"):
            data = enrichment_result.dict()
        elif isinstance(enrichment_result, dict):
            data = dict(enrichment_result)
        else:
            raise TypeError(f"Unsupported M4 result type: {type(enrichment_result)}")

        # 1. Extract the canonical event
        event = data.get("event")
        if not event or not isinstance(event, dict):
            # Fallback: if already unwrapped
            if "schema_version" in data and ("event" in data or "id" in data):
                event = dict(data)
            else:
                raise ValueError("M4 result does not contain a valid canonical 'event' object")
        else:
            event = dict(event)

        # 2. Harmonize Tenant Identity (Resolves P1-2)
        tenant_block = event.get("tenant")
        if isinstance(tenant_block, dict):
            tenant_id = tenant_block.get("tenant_id") or tenant_block.get("id")
            if tenant_id:
                # Ensure BOTH fields exist so both M4 and M5 contracts are satisfied
                tenant_block["tenant_id"] = str(tenant_id)
                tenant_block["id"] = str(tenant_id)
                # Also expose root tenant_id for M5 fallback
                event["tenant_id"] = str(tenant_id)
        elif not tenant_block and "tenant_id" in event:
            event["tenant"] = {
                "id": str(event["tenant_id"]),
                "tenant_id": str(event["tenant_id"]),
            }

        # 3. Preserve M4 Cryptographic Integrity
        m4_integrity = data.get("integrity")
        if m4_integrity:
            if hasattr(m4_integrity, "model_dump"):
                m4_integrity = m4_integrity.model_dump()
            event["integrity"] = m4_integrity

        # 4. Attach enrichment provenance and diagnostics to extensions
        extensions = event.setdefault("extensions", {})
        if "provenance" in data:
            extensions["enrichment_provenance"] = data["provenance"]
        if "diagnostics" in data:
            extensions["enrichment_diagnostics"] = data["diagnostics"]
        if "status" in data:
            extensions["enrichment_status"] = data["status"]

        return event
