"""AuditLog ORM model — append-only audit trail with tenant isolation."""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.tenant import Tenant


class AuditAction(str, enum.Enum):
    # Sources
    SOURCE_CREATED = "SOURCE_CREATED"
    SOURCE_UPDATED = "SOURCE_UPDATED"
    SOURCE_ENABLED = "SOURCE_ENABLED"
    SOURCE_DISABLED = "SOURCE_DISABLED"
    SOURCE_DELETED = "SOURCE_DELETED"
    # Parsers
    PARSER_REGISTERED = "PARSER_REGISTERED"
    PARSER_SUBMITTED = "PARSER_SUBMITTED"
    PARSER_APPROVED = "PARSER_APPROVED"
    PARSER_REJECTED = "PARSER_REJECTED"
    PARSER_ACTIVATED = "PARSER_ACTIVATED"
    PARSER_DISABLED = "PARSER_DISABLED"
    PARSER_ROLLED_BACK = "PARSER_ROLLED_BACK"
    PARSER_UPDATED = "PARSER_UPDATED"
    PARSER_DELETED = "PARSER_DELETED"
    # Schemas
    SCHEMA_CREATED = "SCHEMA_CREATED"
    SCHEMA_VERSION_ADDED = "SCHEMA_VERSION_ADDED"
    SCHEMA_DELETED = "SCHEMA_DELETED"
    # Mappings
    MAPPING_CREATED = "MAPPING_CREATED"
    MAPPING_UPDATED = "MAPPING_UPDATED"
    MAPPING_DELETED = "MAPPING_DELETED"
    # Policies
    POLICY_CREATED = "POLICY_CREATED"
    POLICY_UPDATED = "POLICY_UPDATED"
    POLICY_ENABLED = "POLICY_ENABLED"
    POLICY_DISABLED = "POLICY_DISABLED"
    POLICY_DELETED = "POLICY_DELETED"
    # Configuration & Distribution
    CONFIGURATION_CHANGED = "CONFIGURATION_CHANGED"
    CONFIGURATION_DISTRIBUTED = "CONFIGURATION_DISTRIBUTED"
    CONFIGURATION_ACKNOWLEDGED = "CONFIGURATION_ACKNOWLEDGED"
    CONFIGURATION_FAILED = "CONFIGURATION_FAILED"
    CONFIGURATION_RETRY = "CONFIGURATION_RETRY"
    # Replay
    REPLAY_REQUESTED = "REPLAY_REQUESTED"
    REPLAY_QUEUED = "REPLAY_QUEUED"
    REPLAY_COMPLETED = "REPLAY_COMPLETED"
    REPLAY_FAILED = "REPLAY_FAILED"
    # Auth & Users
    USER_LOGIN = "USER_LOGIN"
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_DELETED = "USER_DELETED"
    USER_ROLE_ASSIGNED = "USER_ROLE_ASSIGNED"
    # Tenants
    TENANT_CREATED = "TENANT_CREATED"
    TENANT_UPDATED = "TENANT_UPDATED"
    TENANT_SUSPENDED = "TENANT_SUSPENDED"
    TENANT_DISABLED = "TENANT_DISABLED"


class AuditResult(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PARTIAL = "PARTIAL"


class AuditLog(UUIDMixin, Base):
    """
    Append-only audit log with strict tenant isolation.
    Never update or delete rows.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_tenant_id", "tenant_id"),
        Index("ix_audit_logs_actor", "actor"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_timestamp", "timestamp"),
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str] = mapped_column(
        String(16), nullable=False, default=AuditResult.SUCCESS.value
    )
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    tenant: Mapped[Tenant | None] = relationship(
        "Tenant", back_populates="audit_logs", lazy="selectin"
    )
