"""
M6 Control Plane — FastAPI application entry point.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from backend.app.api.audit import router as audit_router

# ── Routers ────────────────────────────────────────────────────────────────────
from backend.app.api.auth import router as auth_router
from backend.app.api.configuration import router as configuration_router
from backend.app.api.health import router as health_router
from backend.app.api.kafka import router as kafka_router
from backend.app.api.mappings import router as mappings_router
from backend.app.api.metrics import router as metrics_router
from backend.app.api.parsers import router as parsers_router
from backend.app.api.policies import router as policies_router
from backend.app.api.replay import router as replay_router
from backend.app.api.schemas import router as schemas_router
from backend.app.api.services import router as services_router
from backend.app.api.sources import router as sources_router
from backend.app.api.tenants import router as tenants_router
from backend.app.core.config import get_settings
from backend.app.core.exceptions import (
    M6Error,
    m6_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from backend.app.core.logging import RequestLoggingMiddleware, configure_logging
from backend.app.db.session import dispose_engine, get_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle."""
    settings = get_settings()
    configure_logging(settings.log_level)

    from backend.app.core.logging import get_logger

    logger = get_logger("startup")
    logger.info(
        "M6 Control Plane starting",
        env=settings.app_env,
        version="1.0.0",
        mock_adapters=settings.use_mock_adapters,
    )

    # Touch the engine to validate connection string at startup
    get_engine()

    yield

    # Graceful shutdown
    await dispose_engine()
    logger.info("M6 Control Plane shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ULPF M6 Control Plane",
        description=(
            "Control tower for the Universal Log Processing Framework. "
            "Manages configuration, registries, observability, and deployments. "
            "Does NOT process events — that responsibility belongs to M1–M5."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    # ── Exception handlers ─────────────────────────────────────────────────────
    app.add_exception_handler(M6Error, m6_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_error_handler)  # type: ignore[arg-type]

    # ── Routers ────────────────────────────────────────────────────────────────
    app.include_router(health_router, tags=["Health"])
    app.include_router(metrics_router, tags=["Metrics"])

    API_PREFIX = "/api/v1"
    app.include_router(auth_router, prefix=API_PREFIX, tags=["Authentication"])
    app.include_router(sources_router, prefix=API_PREFIX, tags=["Sources"])
    app.include_router(parsers_router, prefix=API_PREFIX, tags=["Parsers"])
    app.include_router(schemas_router, prefix=API_PREFIX, tags=["Schemas"])
    app.include_router(mappings_router, prefix=API_PREFIX, tags=["Mappings"])
    app.include_router(policies_router, prefix=API_PREFIX, tags=["Policies"])
    app.include_router(services_router, prefix=API_PREFIX, tags=["Services"])
    app.include_router(audit_router, prefix=API_PREFIX, tags=["Audit"])
    app.include_router(replay_router, prefix=API_PREFIX, tags=["Replay"])
    app.include_router(configuration_router, prefix=API_PREFIX, tags=["Configuration"])
    app.include_router(kafka_router, prefix=API_PREFIX, tags=["Kafka"])
    app.include_router(tenants_router, prefix=API_PREFIX, tags=["Tenants"])

    return app


app = create_app()
