"""Service registry ORM model — tracks known external + infrastructure services."""

from __future__ import annotations

import enum

from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import AuditableMixin, Base


class ServiceType(str, enum.Enum):
    MODULE = "module"  # M1-M5
    INFRASTRUCTURE = "infra"  # Kafka, Postgres, Redis, etc.


class ServiceStatus(str, enum.Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class Service(AuditableMixin, Base):
    __tablename__ = "services"

    service_key: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )  # e.g. "m1", "kafka", "opensearch"
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    service_type: Mapped[ServiceType] = mapped_column(
        Enum(ServiceType, name="service_type", native_enum=False), nullable=False
    )
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_status: Mapped[ServiceStatus] = mapped_column(
        Enum(ServiceStatus, name="service_status", native_enum=False),
        default=ServiceStatus.UNKNOWN,
        nullable=False,
    )
