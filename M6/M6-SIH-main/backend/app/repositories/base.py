"""Generic base repository providing common CRUD operations."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, model: type[ModelT], db: AsyncSession) -> None:
        self._model = model
        self._db = db

    async def get(self, id: str) -> ModelT | None:
        return await self._db.get(self._model, id)

    async def list_all(self, *, skip: int = 0, limit: int = 100) -> tuple[Sequence[ModelT], int]:
        count_stmt = select(func.count()).select_from(self._model)
        total: int = (await self._db.execute(count_stmt)).scalar_one()
        stmt = select(self._model).offset(skip).limit(limit)
        items = (await self._db.execute(stmt)).scalars().all()
        return items, total

    async def create(self, obj: ModelT) -> ModelT:
        self._db.add(obj)
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def update(self, obj: ModelT, data: dict[str, Any]) -> ModelT:
        for key, value in data.items():
            if value is not None and hasattr(obj, key):
                setattr(obj, key, value)
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self._db.delete(obj)
        await self._db.flush()

    @staticmethod
    def paginate(total: int, page: int, page_size: int) -> dict[str, int]:
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max(1, math.ceil(total / page_size)) if total else 1,
        }
