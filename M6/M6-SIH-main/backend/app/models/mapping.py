"""Mapping and MappingVersion ORM models — global baselines with optional tenant extensions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import AuditableMixin, Base

if TYPE_CHECKING:
    from backend.app.models.tenant import Tenant


class Mapping(AuditableMixin, Base):
    __tablename__ = "mappings"
    __table_args__ = (
        Index("ix_mappings_mapping_id", "mapping_id"),
        Index("ix_mappings_tenant_id", "tenant_id"),
    )

    mapping_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_format: Mapped[str] = mapped_column(String(128), nullable=False)
    target_schema: Mapped[str] = mapped_column(String(128), nullable=False)
    target_version: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    fields: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Relationships
    tenant: Mapped[Tenant | None] = relationship("Tenant", lazy="selectin")
    versions: Mapped[list[MappingVersion]] = relationship(
        back_populates="mapping",
        cascade="all, delete-orphan",
        order_by="MappingVersion.created_at.desc()",
    )


class MappingVersion(AuditableMixin, Base):
    __tablename__ = "mapping_versions"
    __table_args__ = (Index("ix_mapping_versions_mapping_id", "mapping_id"),)

    mapping_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("mappings.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    fields_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    changed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    mapping: Mapped[Mapping] = relationship(back_populates="versions")
