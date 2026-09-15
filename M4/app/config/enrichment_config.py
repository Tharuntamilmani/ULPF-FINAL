"""Versioned enrichment configuration schema and validation for ULPF M4."""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.common import ConfigLifecycleState

VERSION_REGEX = re.compile(r"^\d+\.\d+\.\d+$")


class ConditionRule(BaseModel):
    """Declarative condition AST node for enrichment rule triggers."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str = Field(..., description="Canonical event field path (e.g. source.ip)")
    operator: str = Field(
        ..., description="Comparison operator: exists, not_exists, equals, in_list, regex_match"
    )
    value: Any | None = Field(default=None, description="Expected value or pattern")

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        valid_ops = {"exists", "not_exists", "equals", "in_list", "regex_match"}
        if v not in valid_ops:
            raise ValueError(f"Invalid condition operator '{v}'. Allowed: {valid_ops}")
        return v


class EnrichmentRuleConfig(BaseModel):
    """Declarative rule triggering specific providers on condition matches."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str
    description: str = ""
    enabled: bool = True
    priority: int = 100
    tenant_scope: list[str] = Field(
        default_factory=lambda: ["*"], description="Target tenants or '*' for all"
    )
    conditions: list[ConditionRule] = Field(default_factory=list)
    providers: list[str] = Field(..., description="Provider IDs triggered by this rule")
    target_namespace: str | None = None


class EnrichmentConfiguration(BaseModel):
    """Versioned immutable configuration controlling M4 execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(..., description="Semantic configuration version (e.g. 1.0.0)")
    description: str = "ULPF M4 Default Enrichment Configuration"
    state: ConfigLifecycleState = Field(default=ConfigLifecycleState.DRAFT)
    enabled_providers: list[str] = Field(
        default_factory=lambda: [
            "asset-local-cmdb",
            "geoip-local-db",
            "threat-intel-local",
        ]
    )
    provider_priorities: dict[str, int] = Field(default_factory=dict)
    provider_timeouts: dict[str, float] = Field(default_factory=dict)
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    rules: list[EnrichmentRuleConfig] = Field(default_factory=list)
    tenant_scopes: list[str] = Field(default_factory=lambda: ["*"])
    max_concurrency: int = 8

    @field_validator("version")
    @classmethod
    def validate_version_format(cls, v: str) -> str:
        if not VERSION_REGEX.match(v.strip()):
            raise ValueError(f"Version must follow semantic versioning (X.Y.Z): {v}")
        return v.strip()
