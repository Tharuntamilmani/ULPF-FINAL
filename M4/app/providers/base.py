"""Provider interface and abstractions for ULPF M4."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.canonical_event import CanonicalEvent
from app.models.common import EnrichmentStatus
from app.models.tenant import TenantContext


class EnrichmentContext(BaseModel):
    """Contextual metadata passed to providers during enrichment execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_context: TenantContext
    configuration_version: str = "1.0.0"
    options: dict[str, Any] = Field(default_factory=dict)


class ProviderOutput(BaseModel):
    """Result returned by an individual enrichment provider."""

    model_config = ConfigDict(extra="forbid")

    status: EnrichmentStatus
    data: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_reference: str | None = None
    error_message: str | None = None
    error_type: str | None = None


class ProviderMetadata(BaseModel):
    """Descriptive metadata for an enrichment provider."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_id: str
    provider_version: str
    target_namespace: str
    priority: int = 100
    timeout_seconds: float = 3.0
    is_tenant_sensitive: bool = True
    capabilities: list[str] = Field(default_factory=list)


class EnrichmentProvider(ABC):
    """Abstract base class for all M4 enrichment providers."""

    def __init__(
        self,
        provider_id: str,
        provider_version: str,
        target_namespace: str,
        priority: int = 100,
        timeout_seconds: float = 3.0,
        is_tenant_sensitive: bool = True,
    ) -> None:
        self.provider_id = provider_id
        self.provider_version = provider_version
        self.target_namespace = target_namespace
        self.priority = priority
        self.timeout_seconds = timeout_seconds
        self.is_tenant_sensitive = is_tenant_sensitive

    @property
    def metadata(self) -> ProviderMetadata:
        """Expose descriptive metadata."""
        return ProviderMetadata(
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            target_namespace=self.target_namespace,
            priority=self.priority,
            timeout_seconds=self.timeout_seconds,
            is_tenant_sensitive=self.is_tenant_sensitive,
        )

    @abstractmethod
    def can_enrich(self, event: CanonicalEvent, context: EnrichmentContext) -> bool:
        """Determine if this provider is applicable to the given canonical event."""
        pass

    @abstractmethod
    def enrich(self, event: CanonicalEvent, context: EnrichmentContext) -> ProviderOutput:
        """Execute enrichment lookup and return normalized provider output."""
        pass
