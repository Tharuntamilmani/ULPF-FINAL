"""Parser Registry service — enforces lifecycle state machine with tenant extensions and automated distribution."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.audit.audit_service import AuditService
from backend.app.core.exceptions import DuplicateError, InvalidStateTransition, ParserNotFound
from backend.app.models.audit_log import AuditAction
from backend.app.models.parser import (
    PARSER_TRANSITIONS,
    Parser,
    ParserStatus,
    ParserVersion,
)
from backend.app.repositories.parser_repo import ParserRepository
from backend.app.schemas.parser import ParserCreate, ParserUpdate
from backend.app.services.config_service import ConfigDistributionService


class ParserRegistry:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = ParserRepository(db)
        self._audit = AuditService(db)
        self._dist = ConfigDistributionService(db)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _assert_transition(self, parser: Parser, target: ParserStatus) -> None:
        allowed = PARSER_TRANSITIONS.get(parser.status, [])
        if target not in allowed:
            raise InvalidStateTransition(
                f"Cannot transition parser '{parser.parser_id}' "
                f"from {parser.status.value} to {target.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

    @staticmethod
    def _snapshot(p: Parser) -> dict[str, Any]:
        return {
            "parser_id": p.parser_id,
            "tenant_id": p.tenant_id,
            "name": p.name,
            "status": p.status.value,
            "version": p.version,
            "vendor": p.vendor,
            "product": p.product,
            "format": p.format,
        }

    async def _transition(
        self,
        id: str,
        target: ParserStatus,
        action: AuditAction,
        actor: str,
        actor_role: str | None,
        tenant_id: str | None = None,
        reason: str | None = None,
        extra_fields: dict[str, Any] | None = None,
    ) -> Parser:
        parser = await self.get(id, tenant_id=tenant_id)
        if tenant_id is not None and parser.tenant_id is None:
            raise InvalidStateTransition("Tenant users cannot modify platform baseline parsers")
        self._assert_transition(parser, target)
        before = self._snapshot(parser)
        parser.status = target
        if extra_fields:
            for k, v in extra_fields.items():
                setattr(parser, k, v)
        await self._repo._db.flush()
        await self._repo.add_version(parser, actor, reason)
        snapshot = self._snapshot(parser)

        await self._audit.record(
            actor=actor,
            actor_role=actor_role,
            action=action,
            resource_type="parser",
            resource_id=parser.parser_id,
            tenant_id=parser.tenant_id,
            version=parser.version,
            before_state=before,
            after_state=snapshot,
            reason=reason,
        )

        # Automatic lifecycle trigger to M2
        op_map = {
            ParserStatus.ACTIVE: "ACTIVATE",
            ParserStatus.DISABLED: "DISABLE",
            ParserStatus.ROLLED_BACK: "ROLLBACK",
        }
        op = op_map.get(target, "UPDATE")

        await self._dist.trigger_propagation(
            config_type="parsers",
            entity_id=parser.parser_id,
            version=parser.version,
            tenant_id=parser.tenant_id,
            operation=op,
            payload=snapshot,
            actor=actor,
            actor_role=actor_role,
        )

        return parser

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def register(
        self,
        data: ParserCreate,
        actor: str,
        actor_role: str | None,
        tenant_id: str | None = None,
    ) -> Parser:
        effective_tenant = data.tenant_id if data.tenant_id is not None else tenant_id
        if await self._repo.parser_id_exists(data.parser_id, tenant_id=effective_tenant):
            scope = f"for tenant '{effective_tenant}'" if effective_tenant else "globally"
            raise DuplicateError(f"Parser '{data.parser_id}' already exists {scope}")
        tags_str = json.dumps(data.tags) if data.tags else None
        parser = Parser(
            parser_id=data.parser_id,
            tenant_id=effective_tenant,
            name=data.name,
            vendor=data.vendor,
            product=data.product,
            format=data.format,
            version=data.version,
            status=ParserStatus.DRAFT,
            description=data.description,
            tags=tags_str,
            created_by=actor,
            updated_by=actor,
        )
        parser = await self._repo.create(parser)
        await self._repo.add_version(parser, actor, "Initial registration")
        snapshot = self._snapshot(parser)

        await self._audit.record(
            actor=actor,
            actor_role=actor_role,
            action=AuditAction.PARSER_REGISTERED,
            resource_type="parser",
            resource_id=parser.parser_id,
            tenant_id=effective_tenant,
            version=parser.version,
            after_state=snapshot,
        )

        await self._dist.trigger_propagation(
            config_type="parsers",
            entity_id=parser.parser_id,
            version=parser.version,
            tenant_id=effective_tenant,
            operation="CREATE",
            payload=snapshot,
            actor=actor,
            actor_role=actor_role,
        )

        return parser

    async def get(self, id: str, tenant_id: str | None = None) -> Parser:
        parser = await self._repo.get_by_id_scoped(id, tenant_id=tenant_id)
        if not parser:
            raise ParserNotFound(f"Parser '{id}' not found")
        return parser

    async def resolve(self, parser_id: str, tenant_id: str | None = None) -> Parser:
        parser = await self._repo.resolve_parser(parser_id, tenant_id=tenant_id)
        if not parser:
            raise ParserNotFound(f"Active parser '{parser_id}' not found")
        return parser

    async def get_by_parser_id(self, parser_id: str, tenant_id: str | None = None) -> Parser:
        parser = await self._repo.get_by_parser_id(parser_id, tenant_id=tenant_id)
        if not parser:
            raise ParserNotFound(f"Parser '{parser_id}' not found")
        return parser

    async def list(
        self,
        *,
        q: str | None = None,
        status: ParserStatus | None = None,
        vendor: str | None = None,
        tenant_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Parser], int]:
        skip = (page - 1) * page_size
        items, total = await self._repo.search(
            q=q,
            status=status,
            vendor=vendor,
            tenant_id=tenant_id,
            skip=skip,
            limit=page_size,
        )
        return list(items), total

    async def update(
        self,
        id: str,
        data: ParserUpdate,
        actor: str,
        actor_role: str | None,
        tenant_id: str | None = None,
    ) -> Parser:
        parser = await self.get(id, tenant_id=tenant_id)
        if tenant_id is not None and parser.tenant_id is None:
            raise InvalidStateTransition("Tenant users cannot modify platform baseline parsers")
        before = self._snapshot(parser)
        update_data: dict[str, Any] = data.model_dump(exclude_none=True)
        if "tags" in update_data:
            update_data["tags"] = json.dumps(update_data["tags"])
        update_data["updated_by"] = actor
        parser = await self._repo.update(parser, update_data)
        snapshot = self._snapshot(parser)

        await self._audit.record(
            actor=actor,
            actor_role=actor_role,
            action=AuditAction.PARSER_UPDATED,
            resource_type="parser",
            resource_id=parser.parser_id,
            tenant_id=parser.tenant_id,
            before_state=before,
            after_state=snapshot,
        )

        await self._dist.trigger_propagation(
            config_type="parsers",
            entity_id=parser.parser_id,
            version=parser.version,
            tenant_id=parser.tenant_id,
            operation="UPDATE",
            payload=snapshot,
            actor=actor,
            actor_role=actor_role,
        )

        return parser

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def submit(
        self,
        id: str,
        actor: str,
        actor_role: str | None,
        reason: str | None = None,
        tenant_id: str | None = None,
    ) -> Parser:
        return await self._transition(
            id,
            ParserStatus.PENDING_APPROVAL,
            AuditAction.PARSER_SUBMITTED,
            actor,
            actor_role,
            tenant_id=tenant_id,
            reason=reason,
        )

    async def approve(
        self,
        id: str,
        actor: str,
        actor_role: str | None,
        reason: str | None = None,
        tenant_id: str | None = None,
    ) -> Parser:
        return await self._transition(
            id,
            ParserStatus.APPROVED,
            AuditAction.PARSER_APPROVED,
            actor,
            actor_role,
            tenant_id=tenant_id,
            reason=reason,
            extra_fields={"approved_by": actor},
        )

    async def activate(
        self,
        id: str,
        actor: str,
        actor_role: str | None,
        reason: str | None = None,
        tenant_id: str | None = None,
    ) -> Parser:
        return await self._transition(
            id,
            ParserStatus.ACTIVE,
            AuditAction.PARSER_ACTIVATED,
            actor,
            actor_role,
            tenant_id=tenant_id,
            reason=reason,
        )

    async def disable(
        self,
        id: str,
        actor: str,
        actor_role: str | None,
        reason: str | None = None,
        tenant_id: str | None = None,
    ) -> Parser:
        return await self._transition(
            id,
            ParserStatus.DISABLED,
            AuditAction.PARSER_DISABLED,
            actor,
            actor_role,
            tenant_id=tenant_id,
            reason=reason,
        )

    async def rollback(
        self,
        id: str,
        actor: str,
        actor_role: str | None,
        reason: str | None = None,
        tenant_id: str | None = None,
    ) -> Parser:
        return await self._transition(
            id,
            ParserStatus.ROLLED_BACK,
            AuditAction.PARSER_ROLLED_BACK,
            actor,
            actor_role,
            tenant_id=tenant_id,
            reason=reason,
        )

    async def get_history(self, id: str, tenant_id: str | None = None) -> Sequence[ParserVersion]:
        parser = await self.get(id, tenant_id=tenant_id)
        return await self._repo.get_versions(parser.id)
