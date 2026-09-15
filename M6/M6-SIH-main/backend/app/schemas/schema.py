"""Schema registry Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from backend.app.models.schema import SchemaStatus
from backend.app.schemas.common import OrmModel


class SchemaVersionCreate(OrmModel):
    version: str = Field(..., min_length=1, max_length=32)
    json_schema: dict[str, Any]
    changelog: str | None = None


class SchemaCreate(OrmModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    initial_version: SchemaVersionCreate | None = None


class SchemaVersionResponse(OrmModel):
    id: str
    schema_id: str
    version: str
    status: SchemaStatus
    json_schema: dict[str, Any]
    changelog: str | None
    created_by: str | None
    created_at: datetime


class SchemaResponse(OrmModel):
    id: str
    name: str
    description: str | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime
    versions: list[SchemaVersionResponse] = Field(default_factory=list)
