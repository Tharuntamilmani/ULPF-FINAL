"""Configuration distribution state machine and target tracking models."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import AuditableMixin, Base


class DistributionStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class DistributionTargetState(AuditableMixin, Base):
    """
    Tracks distribution state per target module (M1, M2, M3, M4, M5).
    Persisted atomically in outbox pattern before dispatch.
    """

    __tablename__ = "distribution_target_states"
    __table_args__ = (
        UniqueConstraint("distribution_id", "target_module", name="uq_dist_target"),
        Index("ix_dist_target_status", "status"),
        Index("ix_dist_target_distribution_id", "distribution_id"),
        Index("ix_dist_target_module", "target_module"),
        Index("ix_dist_target_tenant_id", "tenant_id"),
        Index("ix_dist_target_correlation_id", "correlation_id"),
    )

    distribution_id: Mapped[str] = mapped_column(String(64), nullable=False)
    config_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("configuration_versions.id", ondelete="CASCADE"), nullable=True
    )
    target_module: Mapped[str] = mapped_column(String(16), nullable=False)  # M1, M2, M3, M4, M5
    config_type: Mapped[str] = mapped_column(String(64), nullable=False)  # sources, parsers, etc.
    entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    operation: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # CREATE, UPDATE, DELETE, etc.
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[DistributionStatus] = mapped_column(
        Enum(DistributionStatus, name="distribution_status", native_enum=False),
        default=DistributionStatus.PENDING,
        nullable=False,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ack_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
