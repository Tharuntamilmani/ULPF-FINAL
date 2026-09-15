"""
M3 -> M4 Adapter: M3M4Adapter.

Resolves P0-2 and P1-1:
1. M3 wraps the normalized event in {"event": {"ulpf": {...}}}.
   M4 requires a flat CanonicalEvent with top-level fields (event, source, provenance, etc.) and extra="forbid".
2. M3 drops tenant_id during normalization.
   M4 requires tenant.tenant_id for isolation and policy evaluation.
   The integration layer restores trusted TenantContext from the pipeline context.
3. Preserves authoritative M1 raw_hash in extensions.raw_integrity without overwriting.
4. Sets schema_version = "ues.v1".
5. Packages into an M4 EnrichmentRequest payload.
"""

from typing import Dict, Any, Optional
import json
from datetime import datetime, timezone
from integration.contracts.tenant_context import TenantContext


class M3M4Adapter:
    """
    Adapts M3 NormalizationResult into M4 CanonicalEvent and EnrichmentRequest.
    Restores trusted tenant context dropped by M3.
    """

    @classmethod
    def adapt_to_canonical_event(
        cls,
        m3_result: Any,
        tenant_context: TenantContext,
        fallback_raw_event_id: Optional[str] = None,
        fallback_raw_hash: Optional[str] = None,
        fallback_raw_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract and unwrap M3 event["ulpf"] into a flat, valid M4 CanonicalEvent dictionary.
        """
        if isinstance(m3_result, str):
            data = json.loads(m3_result)
        elif hasattr(m3_result, "model_dump"):
            data = m3_result.model_dump()
        elif hasattr(m3_result, "dict"):
            data = m3_result.dict()
        elif isinstance(m3_result, dict):
            data = dict(m3_result)
        else:
            raise TypeError(f"Unsupported M3 result type: {type(m3_result)}")

        # Check normalization success
        if not data.get("success", False):
            errors = data.get("errors", [])
            raise ValueError(f"Cannot adapt failed M3 NormalizationResult: {errors}")

        # Unwrap outer event envelope
        event_wrapper = data.get("event") or {}
        ulpf = event_wrapper.get("ulpf")
        if not ulpf or not isinstance(ulpf, dict):
            raise ValueError("M3 output missing required 'event.ulpf' structure")

        # 1. Core Event Metadata
        raw_event_data = ulpf.get("event") or {}
        event_id = raw_event_data.get("id") or f"evt_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        timestamp = raw_event_data.get("timestamp") or datetime.now(timezone.utc).isoformat()
        kind = raw_event_data.get("kind") or "event"
        
        type_val = raw_event_data.get("type")
        if isinstance(type_val, str):
            type_val = [type_val]
        elif not isinstance(type_val, list):
            type_val = ["info"]
            
        category_val = raw_event_data.get("category")
        if isinstance(category_val, str):
            category_val = [category_val]
        elif not isinstance(category_val, list):
            category_val = ["general"]

        outcome = raw_event_data.get("outcome") or "unknown"
        duration = raw_event_data.get("duration")

        event_block = {
            "id": str(event_id),
            "timestamp": timestamp,
            "kind": kind,
            "type": type_val,
            "category": category_val,
            "outcome": outcome,
            "duration": duration,
        }

        # 2. Provenance (preserve raw_event_id)
        prov_block = ulpf.get("provenance") or {}
        raw_event_id = (
            prov_block.get("raw_event_id")
            or data.get("raw_event_id")
            or fallback_raw_event_id
        )
        if not raw_event_id:
            raise ValueError("Missing required raw_event_id for provenance")

        provenance_block = {
            "raw_event_id": str(raw_event_id),
            "ingestion_timestamp": prov_block.get("ingestion_timestamp") or datetime.now(timezone.utc).isoformat(),
            "pipeline_id": prov_block.get("pipeline_id") or "ulpf-pipeline",
        }

        # 3. Restore Trusted Tenant Context (Resolves P1-1)
        if not tenant_context or not tenant_context.tenant_id:
            raise ValueError("M3 dropped tenant_id and no trusted TenantContext was supplied")

        tenant_block = {
            "tenant_id": tenant_context.tenant_id,
            "scope": {"source_id": tenant_context.source_id},
        }

        # 4. Filter and clean optional blocks to match M4 exact extra="forbid" schemas
        def clean_dict(d: Optional[Dict[str, Any]], allowed_keys: set) -> Dict[str, Any]:
            if not d or not isinstance(d, dict):
                return {}
            return {k: v for k, v in d.items() if k in allowed_keys and v is not None}

        source_block = clean_dict(
            ulpf.get("source"),
            {"ip", "port", "mac", "nat_ip", "domain", "user"}
        )
        dest_block = clean_dict(
            ulpf.get("destination"),
            {"ip", "port", "mac", "nat_ip", "domain", "user"}
        )
        observer_block = clean_dict(
            ulpf.get("observer"),
            {"hostname", "ip", "type", "version"}
        )
        network_block = clean_dict(
            ulpf.get("network"),
            {"transport", "protocol", "direction", "bytes_in", "bytes_out"}
        )
        if network_block:
            if isinstance(network_block.get("protocol"), dict):
                p_dict = network_block["protocol"]
                network_block["protocol"] = p_dict.get("name") or p_dict.get("transport") or p_dict.get("protocol") or "tcp"
            if isinstance(network_block.get("transport"), dict):
                t_dict = network_block["transport"]
                network_block["transport"] = t_dict.get("name") or t_dict.get("transport") or "tcp"
            if network_block.get("protocol") is not None:
                network_block["protocol"] = str(network_block["protocol"]).lower()
            if network_block.get("transport") is not None:
                network_block["transport"] = str(network_block["transport"]).lower()
        host_block = clean_dict(
            ulpf.get("host"),
            {"id", "name", "hostname", "os", "architecture"}
        )
        identity_block = clean_dict(
            ulpf.get("identity"),
            {"user_id", "username", "email", "domain", "groups"}
        )
        app_block = clean_dict(
            ulpf.get("application"),
            {"name", "version"}
        )
        process_block = clean_dict(
            ulpf.get("process"),
            {"pid", "name", "executable", "command_line"}
        )
        security_block = clean_dict(
            ulpf.get("security"),
            {"severity", "risk_score", "threat_indicator"}
        )
        if not security_block:
            security_block = {"severity": "informational"}

        # Parser block
        p_raw = ulpf.get("parser") or {}
        parser_block = {
            "name": p_raw.get("name") or p_raw.get("id") or "unknown",
            "version": str(p_raw.get("version") or "1.0.0"),
            "parsed_at": p_raw.get("parsed_at") or datetime.now(timezone.utc).isoformat(),
        }

        # Normalization block
        norm_raw = ulpf.get("normalization") or {}
        normalization_block = {
            "schema_target": "ues.v1",
            "normalized_at": norm_raw.get("normalized_at") or datetime.now(timezone.utc).isoformat(),
            "rule_version": str(norm_raw.get("rule_version") or "1.0.0"),
        }

        # Vendor block
        v_raw = ulpf.get("vendor") or {}
        vendor_block = {
            "name": v_raw.get("vendor_id") or v_raw.get("name") or "generic",
            "product": v_raw.get("product") or "generic",
            "version": v_raw.get("version"),
        }

        # Extract authoritative M1 raw digest from M3 integrity / raw or fallbacks
        m3_integrity = ulpf.get("integrity") or {}
        raw_hash = (
            m3_integrity.get("raw_hash")
            or (m3_integrity.get("hash") or {}).get("value")
            or fallback_raw_hash
        )

        m3_raw = ulpf.get("raw") or {}
        storage_ref = m3_raw.get("storage_ref") or fallback_raw_ref

        # Extensions namespace: preserve authoritative raw integrity and storage references
        extensions = dict(ulpf.get("extensions") or {})
        if raw_hash:
            extensions["raw_integrity"] = {
                "algorithm": "sha256",
                "raw_hash": raw_hash,
                "storage_ref": storage_ref,
            }

        # Build flat CanonicalEvent matching M4 schema
        canonical_event: Dict[str, Any] = {
            "schema_version": "ues.v1",
            "event": event_block,
            "observer": observer_block,
            "source": source_block,
            "destination": dest_block,
            "network": network_block,
            "host": host_block,
            "identity": identity_block,
            "application": app_block,
            "process": process_block,
            "security": security_block,
            "parser": parser_block,
            "normalization": normalization_block,
            "provenance": provenance_block,
            "integrity": None,  # M4 calculates post-enrichment digest
            "raw": storage_ref or m3_raw.get("raw"),
            "vendor": vendor_block,
            "extensions": extensions,
            "tenant": tenant_block,
        }

        return canonical_event

    @classmethod
    def adapt(
        cls,
        m3_result: Any,
        tenant_context: TenantContext,
        fallback_raw_event_id: Optional[str] = None,
        fallback_raw_hash: Optional[str] = None,
        fallback_raw_ref: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create full M4 EnrichmentRequest payload.
        """
        canonical_event = cls.adapt_to_canonical_event(
            m3_result=m3_result,
            tenant_context=tenant_context,
            fallback_raw_event_id=fallback_raw_event_id,
            fallback_raw_hash=fallback_raw_hash,
            fallback_raw_ref=fallback_raw_ref,
        )

        request_payload = {
            "event": canonical_event,
            "tenant_context": {
                "tenant_id": tenant_context.tenant_id,
                "scope": {"source_id": tenant_context.source_id},
            },
            "options": options or {},
        }

        return request_payload
