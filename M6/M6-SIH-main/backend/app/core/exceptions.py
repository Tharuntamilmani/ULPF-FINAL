"""
M6 Control Plane — Centralised exception hierarchy and error response model.
All API errors are returned as:
  { "error": { "code": "...", "message": "...", "request_id": "..." } }
"""

from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse

from backend.app.core.logging import get_logger, request_id_var

logger = get_logger("exceptions")


# ── Base ───────────────────────────────────────────────────────────────────────


class M6Error(Exception):
    """Base class for all M6 application errors."""

    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}


# ── 400 ───────────────────────────────────────────────────────────────────────


class ValidationError(M6Error):
    http_status = status.HTTP_400_BAD_REQUEST
    code = "VALIDATION_ERROR"


class InvalidStateTransition(M6Error):
    http_status = status.HTTP_400_BAD_REQUEST
    code = "INVALID_STATE_TRANSITION"


class DuplicateError(M6Error):
    http_status = status.HTTP_409_CONFLICT
    code = "DUPLICATE"


class StaleAckError(M6Error):
    http_status = status.HTTP_409_CONFLICT
    code = "STALE_ACK"


class VersionMismatchError(M6Error):
    http_status = status.HTTP_400_BAD_REQUEST
    code = "VERSION_MISMATCH"


class WrongModuleAckError(M6Error):
    http_status = status.HTTP_400_BAD_REQUEST
    code = "WRONG_MODULE_ACK"


# ── 401 / 403 ─────────────────────────────────────────────────────────────────


class AuthenticationError(M6Error):
    http_status = status.HTTP_401_UNAUTHORIZED
    code = "AUTHENTICATION_FAILED"


class PermissionDenied(M6Error):
    http_status = status.HTTP_403_FORBIDDEN
    code = "PERMISSION_DENIED"


# ── 404 ───────────────────────────────────────────────────────────────────────


class NotFoundError(M6Error):
    http_status = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class SourceNotFound(NotFoundError):
    code = "SOURCE_NOT_FOUND"


class ParserNotFound(NotFoundError):
    code = "PARSER_NOT_FOUND"


class SchemaNotFound(NotFoundError):
    code = "SCHEMA_NOT_FOUND"


class MappingNotFound(NotFoundError):
    code = "MAPPING_NOT_FOUND"


class PolicyNotFound(NotFoundError):
    code = "POLICY_NOT_FOUND"


class UserNotFound(NotFoundError):
    code = "USER_NOT_FOUND"


class ReplayNotFound(NotFoundError):
    code = "REPLAY_NOT_FOUND"


# ── 429 ───────────────────────────────────────────────────────────────────────


class RateLimitError(M6Error):
    http_status = status.HTTP_429_TOO_MANY_REQUESTS
    code = "RATE_LIMIT_EXCEEDED"


# ── 503 ───────────────────────────────────────────────────────────────────────


class ServiceUnavailable(M6Error):
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "SERVICE_UNAVAILABLE"


class ExternalServiceUnavailable(ServiceUnavailable):
    code = "EXTERNAL_SERVICE_UNAVAILABLE"


class ConfigurationDistributionError(ServiceUnavailable):
    code = "CONFIG_DISTRIBUTION_ERROR"


# ── Response helpers ──────────────────────────────────────────────────────────


def _error_response(
    code: str, message: str, http_status: int, extra: dict[str, Any] | None = None
) -> ORJSONResponse:
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id_var.get(""),
        }
    }
    if extra:
        body["error"].update(extra)
    return ORJSONResponse(status_code=http_status, content=body)


# ── FastAPI exception handlers ────────────────────────────────────────────────


async def m6_error_handler(request: Request, exc: M6Error) -> ORJSONResponse:
    logger.warning(
        "Application error",
        code=exc.code,
        message=exc.message,
        status=exc.http_status,
    )
    return _error_response(exc.code, exc.message, exc.http_status, exc.detail or None)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> ORJSONResponse:
    errors = exc.errors()
    logger.warning("Request validation failed", errors=errors)
    return _error_response(
        "VALIDATION_ERROR",
        "Request validation failed",
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        {"fields": errors},
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> ORJSONResponse:
    logger.exception("Unhandled server error", exc_info=exc)
    return _error_response(
        "INTERNAL_ERROR",
        "An unexpected error occurred",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
