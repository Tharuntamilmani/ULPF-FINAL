"""ReplayOperation ORM model."""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import AuditableMixin, Base


class ReplayStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ReplayOperation(AuditableMixin, Base):
    __tablename__ = "replay_operations"

    event_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    status: Mapped[ReplayStatus] = mapped_column(
        Enum(ReplayStatus, name="replay_status", native_enum=False),
        default=ReplayStatus.REQUESTED,
        nullable=False,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
