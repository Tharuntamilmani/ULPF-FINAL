"""Audit log Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.app.schemas.common import OrmModel


class AuditLogResponse(OrmModel):
    id: str
    tenant_id: str | None = None
    timestamp: datetime
    actor: str
    actor_role: str | None
    action: str
    resource_type: str
    resource_id: str | None
    version: str | None
    before_state: dict[str, Any] | None
    after_state: dict[str, Any] | None
    reason: str | None
    result: str
    request_id: str | None
