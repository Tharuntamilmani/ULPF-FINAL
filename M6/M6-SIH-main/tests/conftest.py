"""
pytest configuration and shared fixtures.

All tests run without M1-M5 source code.
USE_MOCK_ADAPTERS=true is forced so external services are never called.
Database tests use SQLite in-memory for speed; integration tests use real Postgres.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

# Force mock adapters and dev-safe secrets before any imports
os.environ.setdefault("USE_MOCK_ADAPTERS", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-minimum!!")
os.environ.setdefault("ADMIN_PASSWORD", "TestAdmin@123")
os.environ.setdefault("POSTGRES_PASSWORD", "testpassword")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("KAFKA_ENABLED", "false")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")


from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import backend.app.models  # noqa: F401
from backend.app.core.security import hash_password
from backend.app.db.base import Base

# ── In-memory SQLite engine for unit/API tests ─────────────────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default asyncio policy."""
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def seeded_db(db_session: AsyncSession) -> AsyncSession:
    """DB session with default tenant + admin user + ADMINISTRATOR role pre-seeded."""
    from backend.app.models.tenant import Tenant, TenantStatus
    from backend.app.models.user import Role, User, UserRole

    # Seed default tenant
    tenant = Tenant(
        id="default-tenant-uuid",
        name="Default Tenant",
        slug="default",
        status=TenantStatus.ACTIVE,
    )
    db_session.add(tenant)
    await db_session.flush()

    role = Role(name="ADMINISTRATOR", description="Full control")
    db_session.add(role)
    await db_session.flush()
    user = User(
        username="admin",
        email="admin@test.local",
        hashed_password=hash_password("Admin@12345"),
        is_superuser=True,
        tenant_id=tenant.id,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    await db_session.commit()
    return db_session


@pytest_asyncio.fixture(scope="function")
async def app_client(seeded_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Test HTTP client against the FastAPI app, with DB overridden to use test session."""
    from backend.app.core.dependencies import dep_db
    from backend.app.main import app

    async def override_db():
        yield seeded_db

    app.dependency_overrides[dep_db] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def auth_headers(app_client: AsyncClient) -> dict[str, str]:
    """Return Authorization headers for the seeded admin user."""
    resp = await app_client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "Admin@12345"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
