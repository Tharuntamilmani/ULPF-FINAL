"""Contract tests for Standalone Canonical UES v1 and Enrichment Result schemas."""

import json
from pathlib import Path

import pytest

from app.contracts.canonical_event import CanonicalEvent
from app.contracts.enrichment_contract import EnrichmentRequest, EnrichmentResult
from app.contracts.integrity_contract import IntegrityMetadata
from app.contracts.provenance_contract import EnrichmentProvenance
from app.models.common import CacheStatus, EnrichmentStatus
from app.models.diagnostics import EnrichmentDiagnostic

SCHEMA_DIR = Path(__file__).parents[2] / "contracts" / "schemas"


def test_canonical_event_model_dump_has_required_contract_keys(
    sample_canonical_event: CanonicalEvent,
) -> None:
    """Verify CanonicalEvent serializes all required top-level contract keys."""
    d = sample_canonical_event.model_dump(mode="json")
    assert d["schema_version"] == "ues.v1"
    assert "event" in d
    assert "provenance" in d
    assert "tenant" in d
    assert "extensions" in d


def test_canonical_event_schema_version_is_ues_v1(
    sample_canonical_event: CanonicalEvent,
) -> None:
    """Ensure CanonicalEvent conforms to ues.v1 schema version specification."""
    assert sample_canonical_event.schema_version == "ues.v1"


def test_enrichment_provenance_contract_fields() -> None:
    """Ensure EnrichmentProvenance model strictly validates all required contract fields."""
    prov = EnrichmentProvenance(
        provider_id="test-prov",
        provider_version="1.0.0",
        enrichment_type="geo",
        confidence=0.95,
        result_status=EnrichmentStatus.SUCCESS,
        cache_status=CacheStatus.MISS,
    )
    d = prov.model_dump(mode="json")
    assert "provider_id" in d
    assert "provider_version" in d
    assert "enrichment_type" in d
    assert "confidence" in d
    assert "result_status" in d
    assert "cache_status" in d
    assert "lookup_timestamp" in d


def test_integrity_metadata_contract_fields() -> None:
    """Ensure IntegrityMetadata strictly complies with algorithm and 64-character hex digest."""
    meta = IntegrityMetadata(
        algorithm="sha256",  # type: ignore[arg-type]
        digest="a" * 64,
        canonicalization="rfc8785",  # type: ignore[arg-type]
        phase="enriched",
    )
    d = meta.model_dump(mode="json")
    assert d["algorithm"] == "sha256"
    assert d["canonicalization"] == "rfc8785"
    assert len(d["digest"]) == 64
    assert d["phase"] == "enriched"


def test_integrity_metadata_rejects_invalid_hex() -> None:
    """Ensure invalid hash digest lengths or characters are rejected by contract."""
    with pytest.raises(ValueError, match="Invalid SHA-256 hex digest"):
        IntegrityMetadata(
            digest="short_digest",
        )


def test_enrichment_request_contract_structure(
    sample_canonical_event: CanonicalEvent,
) -> None:
    """Ensure EnrichmentRequest model conforms to API contract structure."""
    req = EnrichmentRequest(event=sample_canonical_event, options={"bypass_cache": True})
    d = req.model_dump(mode="json")
    assert "event" in d
    assert "options" in d
    assert d["options"]["bypass_cache"] is True


def test_enrichment_result_contract_structure(
    sample_canonical_event: CanonicalEvent,
) -> None:
    """Ensure EnrichmentResult model conforms to API contract structure."""
    meta = IntegrityMetadata(digest="b" * 64)
    diag = EnrichmentDiagnostic(total_duration_ms=12.5)
    res = EnrichmentResult(
        event=sample_canonical_event,
        status=EnrichmentStatus.SUCCESS,
        provenance=[],
        diagnostics=diag,
        integrity=meta,
    )
    d = res.model_dump(mode="json")
    assert "event" in d
    assert "status" in d
    assert "provenance" in d
    assert "diagnostics" in d
    assert "integrity" in d
    assert d["status"] == "SUCCESS"


def test_canonical_json_schema_file_exists() -> None:
    """Verify contracts/schemas/canonical_ues_v1.json exists and is valid JSON."""
    schema_path = SCHEMA_DIR / "canonical_ues_v1.json"
    assert schema_path.exists()
    content = json.loads(schema_path.read_text(encoding="utf-8"))
    assert content["title"] == "CanonicalUESv1"


def test_enrichment_result_json_schema_file_exists() -> None:
    """Verify contracts/schemas/enrichment_result_v1.json exists and is valid JSON."""
    schema_path = SCHEMA_DIR / "enrichment_result_v1.json"
    assert schema_path.exists()
    content = json.loads(schema_path.read_text(encoding="utf-8"))
    assert content["title"] == "EnrichmentResultv1"


def test_tenant_context_contract_serialization() -> None:
    """Verify TenantContext serialization complies with contract."""
    from app.models.tenant import TenantContext

    tc = TenantContext(tenant_id="tenant-prod-9", configuration_version="1.2.0")
    d = tc.model_dump(mode="json")
    assert d["tenant_id"] == "tenant-prod-9"
    assert d["configuration_version"] == "1.2.0"
