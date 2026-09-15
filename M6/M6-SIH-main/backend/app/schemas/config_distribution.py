"""Pydantic schemas for configuration distribution status and acknowledgement."""

from __future__ import annotations

from pydantic import Field

from backend.app.schemas.common import OrmModel


class ModuleAckRequest(OrmModel):
    distribution_id: str = Field(..., min_length=1)
    config_id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    module: str = Field(..., pattern=r"^M[1-5]$")
    status: str = Field(..., pattern=r"^(APPLIED|REJECTED|FAILED)$")
    correlation_id: str = Field(..., min_length=1)
    error: str | None = None


class TargetStatusItem(OrmModel):
    module: str
    status: str
    version: str
    sent_at: str | None = None
    ack_at: str | None = None
    retry_count: int = 0
    error: str | None = None


class DistributionStatusResponse(OrmModel):
    distribution_id: str
    found: bool
    overall_status: str
    targets: list[TargetStatusItem] = Field(default_factory=list)
