"""Schema and SchemaVersion ORM models — platform-global canonical event contracts."""

from __future__ import annotations

import enum
from typing import Any

from sqlalchemy import JSON, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import AuditableMixin, Base


class SchemaStatus(str, enum.Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DRAFT = "draft"


class Schema(AuditableMixin, Base):
    __tablename__ = "schemas"
    __table_args__ = (
        UniqueConstraint("name", name="uq_schemas_name"),
        Index("ix_schemas_name", "name"),
    )

    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    versions: Mapped[list[SchemaVersion]] = relationship(
        back_populates="schema",
        cascade="all, delete-orphan",
        order_by="SchemaVersion.created_at.desc()",
    )


class SchemaVersion(AuditableMixin, Base):
    __tablename__ = "schema_versions"
    __table_args__ = (
        UniqueConstraint("schema_id", "version", name="uq_schema_version"),
        Index("ix_schema_versions_schema_id", "schema_id"),
    )

    schema_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schemas.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[SchemaStatus] = mapped_column(
        Enum(SchemaStatus, name="schema_status", native_enum=False),
        default=SchemaStatus.ACTIVE,
        nullable=False,
    )
    json_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    schema: Mapped[Schema] = relationship(back_populates="versions")
