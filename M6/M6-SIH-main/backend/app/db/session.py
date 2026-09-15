"""
M6 Control Plane — SQLAlchemy async engine and session factory.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            echo=settings.is_development,
            future=True,
            connect_args={"ssl": False},
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _session_factory


# Convenience alias used in dependency injection
AsyncSessionLocal: async_sessionmaker[AsyncSession] = None  # type: ignore[assignment]


def _init_session_local() -> None:
    global AsyncSessionLocal
    AsyncSessionLocal = get_session_factory()


_init_session_local()


async def dispose_engine() -> None:
    """Clean shutdown — dispose connection pool."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
