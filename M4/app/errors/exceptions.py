"""ULPF M4 Error Taxonomy."""

from typing import Any


class M4Error(Exception):
    """Base exception for all M4 module errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidEventError(M4Error):
    """Raised when an incoming event violates the canonical UES contract."""

    pass


class InvalidConfigurationError(M4Error):
    """Raised when an enrichment configuration violates schema or invariants."""

    pass


class ProviderTimeoutError(M4Error):
    """Raised when an enrichment provider exceeds its deadline."""

    pass


class ProviderUnavailableError(M4Error):
    """Raised when an enrichment provider cannot be reached or initialized."""

    pass


class ProviderResponseError(M4Error):
    """Raised when a provider returns a malformed, invalid, or oversized response."""

    pass


class IntegrityMismatchError(M4Error):
    """Raised when cryptographic integrity verification fails."""

    pass


class TenantScopeError(M4Error):
    """Raised when cross-tenant access, leakage, or mismatch is detected."""

    pass


class EnrichmentRuleError(M4Error):
    """Raised when a declarative enrichment rule cannot be parsed or evaluated."""

    pass


class SSRFViolationError(M4Error):
    """Raised when a target URL violates SSRF security boundaries."""

    pass


class RateLimitExceededError(M4Error):
    """Raised when concurrency or request rate bounds are exceeded."""

    pass
