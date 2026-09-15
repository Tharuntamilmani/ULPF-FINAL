"""
User repository — data-access layer for User/Role models with tenant scoping.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.user import Role, User, UserRole


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, user_id: str) -> User | None:
        stmt = select(User).options(selectinload(User.roles)).where(User.id == user_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_and_tenant(self, user_id: str, tenant_id: str) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id, User.tenant_id == tenant_id)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).options(selectinload(User.roles)).where(User.username == username)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).options(selectinload(User.roles)).where(User.email == email)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_users(
        self, *, tenant_id: str | None = None, skip: int = 0, limit: int = 100
    ) -> Sequence[User]:
        stmt = select(User).options(selectinload(User.roles))
        if tenant_id is not None:
            stmt = stmt.where(User.tenant_id == tenant_id)
        stmt = stmt.offset(skip).limit(limit)
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def create(
        self,
        username: str,
        email: str,
        hashed_password: str,
        tenant_id: str | None = None,
        is_superuser: bool = False,
    ) -> User:
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            tenant_id=tenant_id,
            is_superuser=is_superuser,
        )
        self._db.add(user)
        await self._db.flush()
        await self._db.refresh(user)
        return user

    async def assign_role(self, user_id: str, role_id: str) -> None:
        user_role = UserRole(user_id=user_id, role_id=role_id)
        self._db.add(user_role)
        await self._db.flush()

    async def get_role_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_role(self, name: str, description: str = "") -> Role:
        role = Role(name=name, description=description)
        self._db.add(role)
        await self._db.flush()
        return role

    async def list_roles(self) -> Sequence[Role]:
        result = await self._db.execute(select(Role))
        return result.scalars().all()

    async def update(self, user: User, data: dict[str, Any]) -> User:
        for k, v in data.items():
            setattr(user, k, v)
        await self._db.flush()
        await self._db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self._db.delete(user)
        await self._db.flush()

    async def clear_roles(self, user_id: str) -> None:
        from sqlalchemy import delete

        await self._db.execute(delete(UserRole).where(UserRole.user_id == user_id))
        await self._db.flush()
