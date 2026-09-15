"""Policy Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pydantic import Field

from backend.app.schemas.common import OrmModel


class PolicyCondition(OrmModel):
    field: str
    operator: str  # >=, <=, ==, !=, in, not_in, contains
    value: Any


class PolicyCreate(OrmModel):
    policy_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field("1.0.0", max_length=32)
    priority: int = Field(50, ge=0, le=1000)
    conditions: list[PolicyCondition] = Field(default_factory=list)
    destinations: list[str] = Field(default_factory=list)
    description: str | None = None
    is_enabled: bool = True


class PolicyUpdate(OrmModel):
    name: str | None = None
    version: str | None = None
    priority: int | None = Field(None, ge=0, le=1000)
    conditions: list[PolicyCondition] | None = None
    destinations: list[str] | None = None
    description: str | None = None
    reason: str | None = None


class PolicyVersionResponse(OrmModel):
    id: str
    policy_id: str
    version: str
    conditions_snapshot: list[Any]
    destinations_snapshot: list[str]
    changed_by: str | None
    reason: str | None
    created_at: datetime


class PolicyResponse(OrmModel):
    id: str
    tenant_id: str
    policy_id: str
    name: str
    version: str
    priority: int
    conditions: list[Any]
    destinations: list[str]
    is_enabled: bool
    description: str | None
    created_by: str | None
    updated_by: str | None
    created_at: datetime
    updated_at: datetime
