"""Tenant Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from backend.app.models.tenant import TenantStatus
from backend.app.schemas.common import OrmModel


class TenantCreate(OrmModel):
    name: str = Field(..., min_length=1, max_length=128)
    slug: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    status: TenantStatus = TenantStatus.ACTIVE


class TenantUpdate(OrmModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    status: TenantStatus | None = None


class TenantResponse(OrmModel):
    id: str
    name: str
    slug: str
    status: TenantStatus
    created_at: datetime
    updated_at: datetime
