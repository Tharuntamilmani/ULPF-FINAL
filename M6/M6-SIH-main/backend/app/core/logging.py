"""
M6 Control Plane — Structured JSON Logging
All logs are JSON. No secrets are logged.
"""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any, cast

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

# Context variable for per-request correlation ID
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
actor_var: ContextVar[str] = ContextVar("actor", default="anonymous")


def _add_request_id(logger: Any, method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    rid = request_id_var.get("")
    if rid:
        event_dict["request_id"] = rid
    return event_dict


def _add_actor(logger: Any, method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    actor = actor_var.get("anonymous")
    if actor:
        event_dict["actor"] = actor
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog with JSON renderer. Call once at startup."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_request_id,
        _add_actor,
    ]

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)

    # Quieten noisy libraries
    for noisy in ("uvicorn.access", "httpx", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str = "m6") -> structlog.stdlib.BoundLogger:
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach request_id to every request and log access."""

    def __init__(self, app: ASGIApp, service_name: str = "m6-control-plane") -> None:
        super().__init__(app)
        self.service_name = service_name
        self._logger = get_logger("http")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(rid)

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=rid,
            service=self.service_name,
            method=request.method,
            path=request.url.path,
        )

        try:
            response = await call_next(request)
        except Exception:
            self._logger.exception("Unhandled exception")
            raise
        finally:
            structlog.contextvars.unbind_contextvars("method", "path")
            request_id_var.reset(token)

        response.headers["X-Request-ID"] = rid
        self._logger.info(
            "HTTP request",
            status_code=response.status_code,
        )
        return response
