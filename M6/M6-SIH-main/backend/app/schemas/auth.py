"""Auth Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import EmailStr, Field

from backend.app.schemas.common import OrmModel


class LoginRequest(OrmModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(OrmModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    tenant_id: str | None = None
    role: str | None = None


class RoleResponse(OrmModel):
    id: str
    name: str
    description: str


class UserResponse(OrmModel):
    id: str
    username: str
    email: str
    is_active: bool
    is_superuser: bool
    tenant_id: str | None = None
    roles: list[RoleResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class UserCreate(OrmModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = "VIEWER"
    tenant_id: str | None = None


class UserUpdate(OrmModel):
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8)
    role: str | None = None
    is_active: bool | None = None
    tenant_id: str | None = None
