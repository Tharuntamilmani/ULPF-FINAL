"""Mapping registry Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from backend.app.schemas.common import OrmModel


class MappingCreate(OrmModel):
    mapping_id: str = Field(..., min_length=1, max_length=128)
    tenant_id: str | None = None
    name: str = Field(..., min_length=1, max_length=255)
    source_format: str = Field(..., min_length=1, max_length=128)
    target_schema: str = Field(..., min_length=1, max_length=128)
    target_version: str = Field(..., min_length=1, max_length=32)
    version: str = Field("1.0.0", max_length=32)
    fields: dict[str, str]
    description: str | None = None


class MappingUpdate(OrmModel):
    name: str | None = None
    source_format: str | None = None
    target_schema: str | None = None
    target_version: str | None = None
    version: str | None = None
    fields: dict[str, str] | None = None
    description: str | None = None
    reason: str | None = None


class MappingVersionResponse(OrmModel):
    id: str
    mapping_id: str
    version: str
    fields_snapshot: dict[str, Any]
    changed_by: str | None
    reason: str | None
    created_at: datetime


class MappingResponse(OrmModel):
    id: str
    mapping_id: str
    tenant_id: str | None = None
    name: str
    source_format: str
    target_schema: str
    target_version: str
    version: str
    fields: dict[str, Any]
    description: str | None
    is_active: bool
    created_by: str | None
    updated_by: str | None
    created_at: datetime
    updated_at: datetime
