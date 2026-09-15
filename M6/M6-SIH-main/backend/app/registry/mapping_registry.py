"""Mapping Registry service with tenant extensions and automated distribution."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.audit.audit_service import AuditService
from backend.app.core.exceptions import DuplicateError, InvalidStateTransition, MappingNotFound
from backend.app.models.audit_log import AuditAction
from backend.app.models.mapping import Mapping
from backend.app.repositories.mapping_repo import MappingRepository
from backend.app.schemas.mapping import MappingCreate, MappingUpdate
from backend.app.services.config_service import ConfigDistributionService


class MappingRegistry:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = MappingRepository(db)
        self._audit = AuditService(db)
        self._dist = ConfigDistributionService(db)

    async def create(
        self,
        data: MappingCreate,
        actor: str,
        actor_role: str | None,
        tenant_id: str | None = None,
    ) -> Mapping:
        effective_tenant = data.tenant_id if data.tenant_id is not None else tenant_id
        if await self._repo.mapping_id_exists(data.mapping_id, tenant_id=effective_tenant):
            scope = f"for tenant '{effective_tenant}'" if effective_tenant else "globally"
            raise DuplicateError(f"Mapping '{data.mapping_id}' already exists {scope}")
        mapping = Mapping(
            mapping_id=data.mapping_id,
            tenant_id=effective_tenant,
            name=data.name,
            source_format=data.source_format,
            target_schema=data.target_schema,
            target_version=data.target_version,
            version=data.version,
            fields=data.fields,
            description=data.description,
            created_by=actor,
            updated_by=actor,
        )
        mapping = await self._repo.create(mapping)
        await self._repo.add_version(mapping, actor, "Initial version")
        snapshot = self._snapshot(mapping)

        await self._audit.record(
            actor=actor,
            actor_role=actor_role,
            action=AuditAction.MAPPING_CREATED,
            resource_type="mapping",
            resource_id=mapping.mapping_id,
            tenant_id=effective_tenant,
            version=mapping.version,
            after_state=snapshot,
        )

        # Automatic lifecycle trigger to M3
        await self._dist.trigger_propagation(
            config_type="mappings",
            entity_id=mapping.mapping_id,
            version=mapping.version,
            tenant_id=effective_tenant,
            operation="CREATE",
            payload=snapshot,
            actor=actor,
            actor_role=actor_role,
        )

        return mapping

    async def get(self, id: str, tenant_id: str | None = None) -> Mapping:
        mapping = await self._repo.get_by_id_scoped(id, tenant_id=tenant_id)
        if not mapping:
            raise MappingNotFound(f"Mapping '{id}' not found")
        return mapping

    async def resolve(self, mapping_id: str, tenant_id: str | None = None) -> Mapping:
        mapping = await self._repo.resolve_mapping(mapping_id, tenant_id=tenant_id)
        if not mapping:
            raise MappingNotFound(f"Active mapping '{mapping_id}' not found")
        return mapping

    async def get_by_mapping_id(self, mapping_id: str, tenant_id: str | None = None) -> Mapping:
        mapping = await self._repo.get_by_mapping_id(mapping_id, tenant_id=tenant_id)
        if not mapping:
            raise MappingNotFound(f"Mapping '{mapping_id}' not found")
        return mapping

    async def list(
        self,
        *,
        q: str | None = None,
        source_format: str | None = None,
        target_schema: str | None = None,
        tenant_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Mapping], int]:
        skip = (page - 1) * page_size
        items, total = await self._repo.search(
            q=q,
            source_format=source_format,
            target_schema=target_schema,
            tenant_id=tenant_id,
            skip=skip,
            limit=page_size,
        )
        return list(items), total

    async def update(
        self,
        id: str,
        data: MappingUpdate,
        actor: str,
        actor_role: str | None,
        tenant_id: str | None = None,
    ) -> Mapping:
        mapping = await self.get(id, tenant_id=tenant_id)
        if tenant_id is not None and mapping.tenant_id is None:
            raise InvalidStateTransition("Tenant users cannot modify platform baseline mappings")
        before = self._snapshot(mapping)
        update_data: dict[str, Any] = data.model_dump(exclude_none=True)
        reason = update_data.pop("reason", None)
        update_data["updated_by"] = actor
        mapping = await self._repo.update(mapping, update_data)
        await self._repo.add_version(mapping, actor, reason)
        snapshot = self._snapshot(mapping)

        await self._audit.record(
            actor=actor,
            actor_role=actor_role,
            action=AuditAction.MAPPING_UPDATED,
            resource_type="mapping",
            resource_id=mapping.mapping_id,
            tenant_id=mapping.tenant_id,
            version=mapping.version,
            before_state=before,
            after_state=snapshot,
            reason=reason,
        )

        await self._dist.trigger_propagation(
            config_type="mappings",
            entity_id=mapping.mapping_id,
            version=mapping.version,
            tenant_id=mapping.tenant_id,
            operation="UPDATE",
            payload=snapshot,
            actor=actor,
            actor_role=actor_role,
        )

        return mapping

    async def delete(
        self,
        id: str,
        actor: str,
        actor_role: str | None,
        tenant_id: str | None = None,
    ) -> None:
        mapping = await self.get(id, tenant_id=tenant_id)
        if tenant_id is not None and mapping.tenant_id is None:
            raise InvalidStateTransition("Tenant users cannot delete platform baseline mappings")
        before = self._snapshot(mapping)
        await self._repo.delete(mapping)

        await self._audit.record(
            actor=actor,
            actor_role=actor_role,
            action=AuditAction.MAPPING_DELETED,
            resource_type="mapping",
            resource_id=mapping.mapping_id,
            tenant_id=mapping.tenant_id,
            before_state=before,
        )

        await self._dist.trigger_propagation(
            config_type="mappings",
            entity_id=mapping.mapping_id,
            version=mapping.version,
            tenant_id=mapping.tenant_id,
            operation="DELETE",
            payload={"mapping_id": mapping.mapping_id},
            actor=actor,
            actor_role=actor_role,
        )

    @staticmethod
    def _snapshot(m: Mapping) -> dict[str, Any]:
        return {
            "mapping_id": m.mapping_id,
            "tenant_id": m.tenant_id,
            "name": m.name,
            "source_format": m.source_format,
            "target_schema": m.target_schema,
            "target_version": m.target_version,
            "version": m.version,
            "is_active": m.is_active,
        }
