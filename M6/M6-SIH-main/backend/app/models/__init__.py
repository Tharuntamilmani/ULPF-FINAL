"""
Register all ORM models with SQLAlchemy metadata.
Alembic env.py imports this module to ensure all tables are discovered.
"""

from backend.app.models.audit_log import AuditAction, AuditLog, AuditResult
from backend.app.models.config_distribution import (
    DistributionStatus,
    DistributionTargetState,
)
from backend.app.models.config_version import (
    ConfigDistributionStatus,
    ConfigurationVersion,
)
from backend.app.models.mapping import Mapping, MappingVersion
from backend.app.models.parser import Parser, ParserStatus, ParserVersion
from backend.app.models.policy import Policy, PolicyVersion
from backend.app.models.replay import ReplayOperation
from backend.app.models.schema import Schema, SchemaStatus, SchemaVersion
from backend.app.models.service import Service
from backend.app.models.source import Source, SourceStatus
from backend.app.models.tenant import Tenant, TenantStatus
from backend.app.models.user import Role, User, UserRole

__all__ = [
    "Tenant",
    "TenantStatus",
    "User",
    "Role",
    "UserRole",
    "Source",
    "SourceStatus",
    "Parser",
    "ParserVersion",
    "ParserStatus",
    "Schema",
    "SchemaVersion",
    "SchemaStatus",
    "Mapping",
    "MappingVersion",
    "Policy",
    "PolicyVersion",
    "Service",
    "ConfigurationVersion",
    "ConfigDistributionStatus",
    "DistributionTargetState",
    "DistributionStatus",
    "AuditLog",
    "AuditAction",
    "AuditResult",
    "ReplayOperation",
]
