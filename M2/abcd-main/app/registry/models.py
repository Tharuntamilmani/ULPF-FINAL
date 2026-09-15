from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, model_validator


class ParserStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class MatchRule(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    format: Optional[str] = None
    vendor: Optional[str] = None
    product: Optional[str] = None
    header_pattern: Optional[str] = None


class ParserDefinition(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(..., description="Unique parser ID e.g. parser-cisco-asa")
    name: str = Field(..., description="Human readable name")
    tenant_id: str = Field(
        "global", description="Tenant identifier or 'global' for baseline parsers"
    )
    vendor: str = Field("Generic", description="Vendor/Source e.g. Cisco")
    product: str = Field("Generic", description="Product e.g. ASA")
    formats: List[str] = Field(
        default_factory=lambda: ["syslog"], description="Supported format list"
    )
    version: str = Field("1.0.0", description="Semantic parser version")
    mapping_version: str = Field("1.0.0", description="Mapping configuration version")
    priority: int = Field(
        100, description="Priority rank (lower or higher priority lookup)"
    )
    status: ParserStatus = Field(
        ParserStatus.ACTIVE, description="Current parser operational status"
    )
    max_payload_bytes: int = Field(
        100_000, description="Maximum allowed payload length in bytes"
    )

    # Declarative parsing configuration
    match: Optional[MatchRule] = None
    patterns: List[str] = Field(
        default_factory=list, description="List of grok or regex patterns"
    )
    custom_patterns: Dict[str, str] = Field(
        default_factory=dict, description="Custom pattern macros"
    )
    fields: Dict[str, str] = Field(
        default_factory=dict, description="Extracted field mappings"
    )

    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    created_by: str = Field("system", description="Author or system identifier")

    @model_validator(mode="before")
    @classmethod
    def _sanitize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if data.get("vendor") is None:
                data["vendor"] = "Generic"
            if data.get("product") is None:
                data["product"] = "Generic"
            if not data.get("tenant_id"):
                data["tenant_id"] = "global"
        return data
