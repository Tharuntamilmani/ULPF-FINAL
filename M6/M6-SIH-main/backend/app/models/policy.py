"""Policy and PolicyVersion ORM models — strictly tenant-scoped."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import AuditableMixin, Base

if TYPE_CHECKING:
    from backend.app.models.tenant import Tenant


class Policy(AuditableMixin, Base):
    __tablename__ = "policies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "policy_id", name="uq_tenant_policy"),
        Index("ix_policies_tenant_id", "tenant_id"),
        Index("ix_policies_policy_id", "policy_id"),
        Index("ix_policies_priority", "priority"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    policy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    conditions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    destinations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Relationships
    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="policies", lazy="selectin")
    versions: Mapped[list[PolicyVersion]] = relationship(
        back_populates="policy",
        cascade="all, delete-orphan",
        order_by="PolicyVersion.created_at.desc()",
    )


class PolicyVersion(AuditableMixin, Base):
    __tablename__ = "policy_versions"
    __table_args__ = (Index("ix_policy_versions_policy_id", "policy_id"),)

    policy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("policies.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    conditions_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    destinations_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    changed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    policy: Mapped[Policy] = relationship(back_populates="versions")
