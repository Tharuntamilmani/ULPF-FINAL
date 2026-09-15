"""Common enumerations and types for ULPF M4."""

from enum import Enum


class EnrichmentStatus(str, Enum):
    """Execution status of an enrichment attempt."""

    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    TIMEOUT = "TIMEOUT"
    NOT_FOUND = "NOT_FOUND"


class CacheStatus(str, Enum):
    """Cache lookup status."""

    HIT = "HIT"
    MISS = "MISS"
    BYPASS = "BYPASS"


class IntegrityAlgorithm(str, Enum):
    """Supported cryptographic hash algorithms."""

    SHA256 = "sha256"


class CanonicalizationAlgorithm(str, Enum):
    """Supported canonicalization schemes."""

    RFC8785 = "rfc8785"


class ConfigLifecycleState(str, Enum):
    """State machine states for enrichment configuration."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ROLLED_BACK = "rolled_back"


class ApiRole(str, Enum):
    """Role-based access control roles for M4 APIs."""

    EVENT_PROCESSING = "event_processing"
    ANALYST_READ = "analyst_read"
    ADMIN = "admin"
