"""Tenant model and isolation context for ULPF M4."""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

TENANT_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]{1,128}$")


class TenantContext(BaseModel):
    """Encapsulates tenant identity and boundaries for enrichment processing."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_id: str = Field(..., description="Unique identifier for the tenant")
    scope: dict[str, Any] = Field(
        default_factory=dict, description="Tenant-specific scopes/attributes"
    )
    configuration_version: str = Field(
        default="1.0.0", description="Configuration version bound to this tenant"
    )

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("tenant_id cannot be empty")
        v_clean = v.strip()
        if not TENANT_ID_REGEX.match(v_clean):
            raise ValueError(f"Invalid tenant_id format: {v_clean}")
        return v_clean
