"""FastAPI entrypoint and application factory for ULPF M4."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.routes import router as core_router
from app.config.settings import Settings
from app.errors.exceptions import (
    InvalidEventError,
    M4Error,
    SSRFViolationError,
    TenantScopeError,
)
from app.observability.logging import setup_logging

settings = Settings()
logger = setup_logging(level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown hooks."""
    logger.info("Starting ULPF Module M4 Enrichment Engine")
    yield
    logger.info("Shutting down ULPF Module M4 Enrichment Engine")


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    app = FastAPI(
        title="ULPF Module M4 — Enrichment + Provenance + Integrity",
        description="Independent, production-grade enrichment, provenance lineage, and integrity engine.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom Exception Handlers
    @app.exception_handler(InvalidEventError)
    async def invalid_event_handler(request: Request, exc: InvalidEventError) -> JSONResponse:
        logger.warning(f"Invalid canonical event: {exc}")
        return JSONResponse(
            status_code=400,
            content={"error": "InvalidEventError", "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(TenantScopeError)
    async def tenant_scope_handler(request: Request, exc: TenantScopeError) -> JSONResponse:
        logger.warning(f"Tenant boundary violation: {exc}")
        return JSONResponse(
            status_code=403,
            content={"error": "TenantScopeError", "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(SSRFViolationError)
    async def ssrf_handler(request: Request, exc: SSRFViolationError) -> JSONResponse:
        logger.error(f"SSRF violation attempt: {exc}")
        return JSONResponse(
            status_code=400,
            content={"error": "SSRFViolationError", "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(M4Error)
    async def m4_error_handler(request: Request, exc: M4Error) -> JSONResponse:
        logger.error(f"M4 Module Error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": type(exc).__name__, "message": exc.message, "details": exc.details},
        )

    # Mount API routers
    app.include_router(health_router)
    app.include_router(core_router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
