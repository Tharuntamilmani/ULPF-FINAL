"""Replay Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from backend.app.models.replay import ReplayStatus
from backend.app.schemas.common import OrmModel


class ReplayRequest(OrmModel):
    source: str | None = None
    reason: str | None = Field(None, max_length=512)


class ReplayResponse(OrmModel):
    id: str
    event_id: str
    source: str | None
    reason: str | None
    requested_by: str
    requested_at: datetime
    status: ReplayStatus
    error_message: str | None
    completed_at: datetime | None
    created_at: datetime
