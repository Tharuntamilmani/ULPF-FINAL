"""Configurable mock provider for testing and resilience verification."""

import time
from typing import Any

from app.contracts.canonical_event import CanonicalEvent
from app.errors.exceptions import (
    ProviderTimeoutError,
)
from app.models.common import EnrichmentStatus
from app.providers.base import EnrichmentContext, EnrichmentProvider, ProviderOutput


class MockEnrichmentProvider(EnrichmentProvider):
    """Mock enrichment provider with configurable behavior for testing."""

    def __init__(
        self,
        provider_id: str = "mock-provider",
        provider_version: str = "1.0.0",
        target_namespace: str = "mock",
        priority: int = 50,
        timeout_seconds: float = 1.0,
        is_tenant_sensitive: bool = True,
        mock_data: dict[str, Any] | None = None,
        confidence: float = 0.9,
        should_fail: bool = False,
        should_timeout: bool = False,
        should_not_found: bool = False,
        raise_exception: Exception | None = None,
        delay_seconds: float = 0.0,
        applicable: bool = True,
    ) -> None:
        super().__init__(
            provider_id=provider_id,
            provider_version=provider_version,
            target_namespace=target_namespace,
            priority=priority,
            timeout_seconds=timeout_seconds,
            is_tenant_sensitive=is_tenant_sensitive,
        )
        self.mock_data = mock_data or {"annotated": True, "label": "test_tag"}
        self.confidence = confidence
        self.should_fail = should_fail
        self.should_timeout = should_timeout
        self.should_not_found = should_not_found
        self.raise_exception = raise_exception
        self.delay_seconds = delay_seconds
        self.applicable = applicable
        self.call_count = 0

    def can_enrich(self, event: CanonicalEvent, context: EnrichmentContext) -> bool:
        return self.applicable

    def enrich(self, event: CanonicalEvent, context: EnrichmentContext) -> ProviderOutput:
        self.call_count += 1

        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)

        if self.should_timeout:
            raise ProviderTimeoutError(
                f"Provider '{self.provider_id}' exceeded timeout limit of {self.timeout_seconds}s"
            )

        if self.raise_exception:
            raise self.raise_exception

        if self.should_fail:
            return ProviderOutput(
                status=EnrichmentStatus.FAILED,
                confidence=0.0,
                error_message="Simulated provider failure",
                error_type="MockFailure",
            )

        if self.should_not_found:
            return ProviderOutput(
                status=EnrichmentStatus.NOT_FOUND,
                confidence=0.0,
                error_message="Entity not found in mock store",
            )

        return ProviderOutput(
            status=EnrichmentStatus.SUCCESS,
            data=dict(self.mock_data),
            confidence=self.confidence,
            source_reference=f"mock://{self.provider_id}/v{self.provider_version}",
        )
