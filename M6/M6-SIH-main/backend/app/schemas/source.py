"""Source Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from backend.app.models.source import SourceStatus
from backend.app.schemas.common import OrmModel


class SourceCreate(OrmModel):
    source_id: str = Field(..., min_length=1, max_length=128)
    tenant_id: str = Field("default", max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    vendor: str = Field(..., min_length=1, max_length=128)
    product: str = Field(..., min_length=1, max_length=128)
    source_type: str = Field(..., min_length=1, max_length=64)
    protocol: str = Field(..., min_length=1, max_length=64)
    transport: str = Field(..., min_length=1, max_length=32)
    port: int | None = Field(None, ge=1, le=65535)
    zone: str | None = Field(None, max_length=64)
    parser_id: str | None = Field(None, max_length=128)
    description: str | None = None
    tags: list[str] | None = None


class SourceUpdate(OrmModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    vendor: str | None = None
    product: str | None = None
    source_type: str | None = None
    protocol: str | None = None
    transport: str | None = None
    port: int | None = Field(None, ge=1, le=65535)
    zone: str | None = None
    parser_id: str | None = None
    description: str | None = None
    tags: list[str] | None = None


class SourceResponse(OrmModel):
    id: str
    source_id: str
    tenant_id: str
    name: str
    vendor: str
    product: str
    source_type: str
    protocol: str
    transport: str
    port: int | None
    zone: str | None
    status: SourceStatus
    parser_id: str | None
    description: str | None
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    updated_by: str | None

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v: Any) -> list[str] | None:
        import json

        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
                return [v]
            except Exception:
                return [v]
        if isinstance(v, list):
            return [str(item) for item in v]
        return None
