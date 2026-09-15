"""
M6 Control Plane — FastAPI dependency providers.
Provides: database sessions, settings, current user.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import Settings, get_settings
from backend.app.core.security import decode_access_token
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Settings ───────────────────────────────────────────────────────────────────


async def dep_settings() -> Settings:
    return get_settings()


DepSettings = Annotated[Settings, Depends(dep_settings)]


# ── Database session ───────────────────────────────────────────────────────────


async def dep_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DepDB = Annotated[AsyncSession, Depends(dep_db)]


# ── Current user (lazy import to avoid circular deps) ─────────────────────────


async def dep_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DepDB,
) -> User:
    """Validate JWT and return the User ORM object."""
    from backend.app.repositories.user_repo import UserRepository  # lazy import

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    if user.tenant_id:
        from backend.app.models.tenant import TenantStatus
        from backend.app.repositories.tenant_repo import TenantRepository

        tenant = await TenantRepository(db).get(user.tenant_id)
        if not tenant or tenant.status != TenantStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant account is suspended or disabled",
            )
    return user


# Re-export as annotated alias (used in route signatures)
# Usage: async def route(current_user: CurrentUser, ...)
CurrentUser = Annotated[User, Depends(dep_current_user)]
