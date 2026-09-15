"""
Audit service — centralised write point for all audit events.
Enforces append-only semantics. Never modifies existing rows.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import get_logger, request_id_var
from backend.app.models.audit_log import AuditAction, AuditLog, AuditResult
from backend.app.repositories.audit_repo import AuditRepository

logger = get_logger("audit")


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = AuditRepository(db)

    async def record(
        self,
        *,
        actor: str,
        actor_role: str | None,
        action: AuditAction,
        resource_type: str,
        resource_id: str | None = None,
        tenant_id: str | None = None,
        version: str | None = None,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        reason: str | None = None,
        result: AuditResult = AuditResult.SUCCESS,
        extra: dict[str, Any] | None = None,
    ) -> AuditLog:
        rid = request_id_var.get("")
        entry = await self._repo.append(
            actor=actor,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            version=version,
            before_state=before_state,
            after_state=after_state,
            reason=reason,
            result=result,
            request_id=rid or None,
            extra=extra,
        )
        logger.info(
            "Audit event recorded",
            actor=actor,
            action=action.value,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            result=result.value,
        )
        return entry
