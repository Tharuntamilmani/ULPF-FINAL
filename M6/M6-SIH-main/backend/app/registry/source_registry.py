"""Source Registry service with strict tenant isolation and automatic configuration propagation."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.audit.audit_service import AuditService
from backend.app.core.exceptions import DuplicateError, SourceNotFound
from backend.app.models.audit_log import AuditAction
from backend.app.models.source import Source, SourceStatus
from backend.app.repositories.source_repo import SourceRepository
from backend.app.schemas.source import SourceCreate, SourceUpdate
from backend.app.services.config_service import ConfigDistributionService


class SourceRegistry:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = SourceRepository(db)
        self._audit = AuditService(db)
        self._dist = ConfigDistributionService(db)

    async def create(
        self,
        data: SourceCreate,
        actor: str,
        actor_role: str | None,
        tenant_id: str = "default-tenant-uuid",
    ) -> Source:
        if await self._repo.source_id_exists(data.source_id, tenant_id=tenant_id):
            raise DuplicateError(f"Source '{data.source_id}' already exists for tenant")

        tags_str = json.dumps(data.tags) if data.tags else None
        source = Source(
            source_id=data.source_id,
            tenant_id=tenant_id,
            name=data.name,
            vendor=data.vendor,
            product=data.product,
            source_type=data.source_type,
            protocol=data.protocol,
            transport=data.transport,
            port=data.port,
            zone=data.zone,
            parser_id=data.parser_id,
            description=data.description,
            tags=tags_str,
            created_by=actor,
            updated_by=actor,
        )
        source = await self._repo.create(source)
        snapshot = self._snapshot(source)

        await self._audit.record(
            actor=actor,
            actor_role=actor_role,
            action=AuditAction.SOURCE_CREATED,
            resource_type="source",
            resource_id=source.source_id,
            tenant_id=tenant_id,
            after_state=snapshot,
        )

        # Automatic lifecycle trigger: propagate to M1
        await self._dist.trigger_propagation(
            config_type="sources",
            entity_id=source.source_id,
            version="1.0.0",
            tenant_id=tenant_id,
            operation="CREATE",
            payload=snapshot,
            actor=actor,
            actor_role=actor_role,
        )

        return source

    async def get(self, id: str, tenant_id: str | None = None) -> Source:
        source = await self._repo.get_by_id_and_tenant(id, tenant_id=tenant_id)
        if not source:
            raise SourceNotFound(f"Source '{id}' not found")
        return source

    async def get_by_source_id(self, source_id: str, tenant_id: str | None = None) -> Source:
        source = await self._repo.get_by_source_id(source_id, tenant_id=tenant_id)
        if not source:
            raise SourceNotFound(f"Source '{source_id}' not found")
        return source

    async def list(
        self,
        *,
        q: str | None = None,
        vendor: str | None = None,
        status: SourceStatus | None = None,
        tenant_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Source], int]:
        skip = (page - 1) * page_size
        items, total = await self._repo.search(
            q=q,
            vendor=vendor,
            status=status,
            tenant_id=tenant_id,
            skip=skip,
            limit=page_size,
        )
        return list(items), total

    async def update(
        self,
        id: str,
        data: SourceUpdate,
        actor: str,
        actor_role: str | None,
        tenant_id: str | None = None,
    ) -> Source:
        source = await self.get(id, tenant_id=tenant_id)
        before = self._snapshot(source)
        update_data: dict[str, Any] = data.model_dump(exclude_none=True)
        # Ensure tenant ownership cannot be mutated
        update_data.pop("tenant_id", None)
        if "tags" in update_data:
            update_data["tags"] = json.dumps(update_data["tags"])
        update_data["updated_by"] = actor
        source = await self._repo.update(source, update_data)
        snapshot = self._snapshot(source)

        await self._audit.record(
            actor=actor,
            actor_role=actor_role,
            action=AuditAction.SOURCE_UPDATED,
            resource_type="source",
            resource_id=source.source_id,
            tenant_id=source.tenant_id,
            before_state=before,
            after_state=snapshot,
        )

        # Automatic lifecycle trigger: propagate update to M1
        await self._dist.trigger_propagation(
            config_type="sources",
            entity_id=source.source_id,
            version="1.0.0",
            tenant_id=source.tenant_id,
            operation="UPDATE",
            payload=snapshot,
            actor=actor,
            actor_role=actor_role,
        )

        return source

    async def delete(
        self, id: str, actor: str, actor_role: str | None, tenant_id: str | None = None
    ) -> None:
        source = await self.get(id, tenant_id=tenant_id)
        before = self._snapshot(source)
        await self._repo.delete(source)

        await self._audit.record(
            actor=actor,
            actor_role=actor_role,
            action=AuditAction.SOURCE_DELETED,
            resource_type="source",
            resource_id=source.source_id,
            tenant_id=source.tenant_id,
            before_state=before,
        )

        # Automatic lifecycle trigger: propagate deletion to M1
        await self._dist.trigger_propagation(
            config_type="sources",
            entity_id=source.source_id,
            version="1.0.0",
            tenant_id=source.tenant_id,
            operation="DELETE",
            payload={"source_id": source.source_id},
            actor=actor,
            actor_role=actor_role,
        )

    async def enable(
        self, id: str, actor: str, actor_role: str | None, tenant_id: str | None = None
    ) -> Source:
        source = await self.get(id, tenant_id=tenant_id)
        source.status = SourceStatus.ACTIVE
        source.updated_by = actor
        await self._db.flush()
        snapshot = self._snapshot(source)

        await self._audit.record(
            actor=actor,
            actor_role=actor_role,
            action=AuditAction.SOURCE_ENABLED,
            resource_type="source",
            resource_id=source.source_id,
            tenant_id=source.tenant_id,
            after_state=snapshot,
        )

        await self._dist.trigger_propagation(
            config_type="sources",
            entity_id=source.source_id,
            version="1.0.0",
            tenant_id=source.tenant_id,
            operation="ENABLE",
            payload=snapshot,
            actor=actor,
            actor_role=actor_role,
        )

        return source

    async def disable(
        self, id: str, actor: str, actor_role: str | None, tenant_id: str | None = None
    ) -> Source:
        source = await self.get(id, tenant_id=tenant_id)
        source.status = SourceStatus.DISABLED
        source.updated_by = actor
        await self._db.flush()
        snapshot = self._snapshot(source)

        await self._audit.record(
            actor=actor,
            actor_role=actor_role,
            action=AuditAction.SOURCE_DISABLED,
            resource_type="source",
            resource_id=source.source_id,
            tenant_id=source.tenant_id,
            after_state=snapshot,
        )

        await self._dist.trigger_propagation(
            config_type="sources",
            entity_id=source.source_id,
            version="1.0.0",
            tenant_id=source.tenant_id,
            operation="DISABLE",
            payload=snapshot,
            actor=actor,
            actor_role=actor_role,
        )

        return source

    @staticmethod
    def _snapshot(source: Source) -> dict[str, Any]:
        return {
            "source_id": source.source_id,
            "tenant_id": source.tenant_id,
            "name": source.name,
            "status": source.status.value,
            "vendor": source.vendor,
            "product": source.product,
            "source_type": source.source_type,
            "protocol": source.protocol,
            "transport": source.transport,
            "port": source.port,
            "zone": source.zone,
        }
