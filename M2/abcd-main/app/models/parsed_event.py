from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class ClassificationResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    format: str = Field(
        ...,
        description="Detected format: json, syslog, cef, leef, csv, xml, kv, plain_text",
    )
    vendor: Optional[str] = Field(
        "Unknown",
        description="Detected vendor/source (Cisco, Fortinet, Palo Alto, Linux, etc.)",
    )
    product: Optional[str] = Field(
        "Unknown", description="Detected product (ASA, FortiGate, PAN-OS, etc.)"
    )
    confidence: float = Field(
        ..., description="Classification confidence score (0.0 to 1.0)"
    )


class ParserInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Registered parser ID")
    name: str = Field(..., description="Human-readable parser name")
    version: str = Field(..., description="Semantic version of parser")
    confidence: float = Field(1.0, description="Parser execution confidence score")


def _empty_dict() -> Dict[str, Any]:
    return {}


def _empty_list() -> List[str]:
    return []


class ParsedEvent(BaseModel):
    """Frozen M2 -> M3 Outbound Contract Model. Extracted fields remain un-normalized source fields."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "schema_version": "1.0.0",
                "raw_event_id": "raw_01JXYZ789",
                "tenant_id": "tenant-default",
                "source_id": "src-cisco-asa-01",
                "status": "PARSED",
                "classification": {
                    "format": "syslog",
                    "vendor": "Cisco",
                    "product": "ASA",
                    "confidence": 0.99,
                },
                "parser": {
                    "id": "parser-cisco-asa",
                    "name": "Cisco ASA Parser",
                    "version": "1.2.0",
                    "confidence": 0.99,
                },
                "fields": {
                    "timestamp": "2026-09-12T04:00:15.123Z",
                    "srcip": "192.168.10.25",
                    "dstip": "8.8.8.8",
                    "srcport": 51542,
                    "dstport": 443,
                    "action": "allow",
                    "message_id": "302013",
                    "connection_id": "847392",
                },
                "unmapped_fields": [],
                "raw_reference": "s3://raw-logs/tenant-default/2026/09/12/raw_01JXYZ789.log",
                "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "processing_time_ms": 0.45,
                "metadata": {},
            }
        },
    )

    schema_version: str = Field("1.0.0", description="Contract schema version")
    raw_event_id: str = Field(..., description="Reference ID matching RawEventEnvelope")
    tenant_id: str = Field(
        "tenant-default",
        description="Tenant identifier propagated from RawEventEnvelope",
    )
    source_id: Optional[str] = Field(
        None, description="Source device/collector ID propagated from M1"
    )
    status: str = Field(
        "PARSED", description="Parsing status: PARSED, UNPARSED, FAILED"
    )
    classification: ClassificationResult = Field(
        ..., description="Classification metadata from M2 format detector"
    )
    parser: ParserInfo = Field(..., description="Parser metadata used for extraction")
    fields: Dict[str, Any] = Field(
        default_factory=_empty_dict,
        description="Extracted source-specific structured fields (un-normalized)",
    )
    unmapped_fields: List[str] = Field(
        default_factory=_empty_list,
        description="Fields extracted but unmapped to standard keys",
    )
    raw_reference: Optional[str] = Field(
        None, description="URI or object reference to raw blob in cold storage"
    )
    sha256: Optional[str] = Field(
        None, description="SHA-256 digest of original raw event"
    )
    processing_time_ms: Optional[float] = Field(
        0.0, description="Processing duration in milliseconds"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=_empty_dict, description="Operational metadata and diagnostics"
    )
