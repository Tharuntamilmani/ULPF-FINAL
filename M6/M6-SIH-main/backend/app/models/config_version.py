"""ConfigurationVersion ORM model — tracks config distribution snapshots."""

from __future__ import annotations

import enum
from typing import Any

from sqlalchemy import JSON, BigInteger, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import AuditableMixin, Base


class ConfigDistributionStatus(str, enum.Enum):
    PENDING = "pending"
    DISTRIBUTED = "distributed"
    FAILED = "failed"
    PARTIAL = "partial"


class ConfigurationVersion(AuditableMixin, Base):
    __tablename__ = "configuration_versions"

    version: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    config_key: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )  # e.g. "sources", "parsers"
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[ConfigDistributionStatus] = mapped_column(
        Enum(ConfigDistributionStatus, name="config_dist_status", native_enum=False),
        default=ConfigDistributionStatus.PENDING,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    distributed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    redis_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
