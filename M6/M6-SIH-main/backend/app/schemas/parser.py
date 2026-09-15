"""Parser Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from backend.app.models.parser import ParserStatus
from backend.app.schemas.common import OrmModel


class ParserCreate(OrmModel):
    parser_id: str = Field(..., min_length=1, max_length=128)
    tenant_id: str | None = None
    name: str = Field(..., min_length=1, max_length=255)
    vendor: str = Field(..., min_length=1, max_length=128)
    product: str = Field(..., min_length=1, max_length=128)
    format: str = Field(..., min_length=1, max_length=64)
    version: str = Field("1.0.0", max_length=32)
    description: str | None = None
    tags: list[str] | None = None


class ParserUpdate(OrmModel):
    name: str | None = None
    vendor: str | None = None
    product: str | None = None
    format: str | None = None
    version: str | None = None
    description: str | None = None
    tags: list[str] | None = None


class ParserVersionResponse(OrmModel):
    id: str
    parser_id: str
    version: str
    status: ParserStatus
    changed_by: str | None
    reason: str | None
    created_at: datetime


class ParserResponse(OrmModel):
    id: str
    parser_id: str
    tenant_id: str | None = None
    name: str
    vendor: str
    product: str
    format: str
    version: str
    status: ParserStatus
    description: str | None
    tags: list[str] | None = None
    created_by: str | None
    updated_by: str | None
    approved_by: str | None
    created_at: datetime
    updated_at: datetime


class ParserLifecycleRequest(OrmModel):
    reason: str | None = None
