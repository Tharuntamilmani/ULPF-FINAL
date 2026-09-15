"""Parser and ParserVersion ORM models — global baselines with optional tenant extensions."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import AuditableMixin, Base

if TYPE_CHECKING:
    from backend.app.models.tenant import Tenant


class ParserStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    ROLLED_BACK = "ROLLED_BACK"


# Valid state-machine transitions
PARSER_TRANSITIONS: dict[ParserStatus, list[ParserStatus]] = {
    ParserStatus.DRAFT: [ParserStatus.PENDING_APPROVAL],
    ParserStatus.PENDING_APPROVAL: [ParserStatus.APPROVED, ParserStatus.DRAFT],
    ParserStatus.APPROVED: [ParserStatus.ACTIVE],
    ParserStatus.ACTIVE: [ParserStatus.DISABLED, ParserStatus.ROLLED_BACK],
    ParserStatus.ROLLED_BACK: [ParserStatus.ACTIVE],
    ParserStatus.DISABLED: [ParserStatus.ACTIVE],
}


class Parser(AuditableMixin, Base):
    __tablename__ = "parsers"
    __table_args__ = (
        Index("ix_parsers_parser_id", "parser_id"),
        Index("ix_parsers_tenant_id", "tenant_id"),
        Index("ix_parsers_status", "status"),
    )

    parser_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor: Mapped[str] = mapped_column(String(128), nullable=False)
    product: Mapped[str] = mapped_column(String(128), nullable=False)
    format: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. syslog, cef
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    status: Mapped[ParserStatus] = mapped_column(
        Enum(ParserStatus, name="parser_status", native_enum=False),
        default=ParserStatus.DRAFT,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Relationships
    tenant: Mapped[Tenant | None] = relationship("Tenant", lazy="selectin")
    versions: Mapped[list[ParserVersion]] = relationship(
        back_populates="parser",
        cascade="all, delete-orphan",
        order_by="ParserVersion.created_at.desc()",
    )


class ParserVersion(AuditableMixin, Base):
    __tablename__ = "parser_versions"
    __table_args__ = (Index("ix_parser_versions_parser_id", "parser_id"),)

    parser_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parsers.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[ParserStatus] = mapped_column(
        Enum(ParserStatus, name="parser_status", native_enum=False), nullable=False
    )
    changed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    parser: Mapped[Parser] = relationship(back_populates="versions")
