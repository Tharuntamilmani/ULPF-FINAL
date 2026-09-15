"""Policy management service with strict tenant isolation and automated distribution."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.audit.audit_service import AuditService
from backend.app.core.exceptions import DuplicateError, PolicyNotFound
from backend.app.models.audit_log import AuditAction
from backend.app.models.policy import Policy
from backend.app.repositories.policy_repo import PolicyRepository
from backend.app.schemas.policy import PolicyCreate, PolicyUpdate
from backend.app.services.config_service import ConfigDistributionService


class PolicyRegistry:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = PolicyRepository(db)
        self._audit = AuditService(db)
        self._dist = ConfigDistributionService(db)

    async def create(
        self,
        data: PolicyCreate,
        actor: str,
        actor_role: str | None,
        tenant_id: str = "default-tenant-uuid",
    ) -> Policy:
        if await self._repo.policy_id_exists(data.policy_id, tenant_id=tenant_id):
            raise DuplicateError(f"Policy '{data.policy_id}' already exists for tenant")

        conds = [c.model_dump() if hasattr(c, "model_dump") else c for c in data.conditions]
        policy = Policy(
            policy_id=data.policy_id,
            tenant_id=tenant_id,
            name=data.name,
            version=data.version,
            priority=data.priority,
            conditions=conds,
            destinations=data.destinations,
            is_enabled=data.is_enabled,
            description=data.description,
            created_by=actor,
            updated_by=actor,
        )
        policy = await self._repo.create(policy)
        await self._repo.add_version(policy, actor, "Initial version")
        snapshot = self._snapshot(policy)

        await self._audit.record(
            actor=actor,
            actor_role=actor_role,
            action=AuditAction.POLICY_CREATED,
            resource_type="policy",
            resource_id=policy.policy_id,
            tenant_id=tenant_id,
            version=policy.version,
            after_state=snapshot,
        )

        # Automatic lifecycle trigger: propagate to M5
        await self._dist.trigger_propagation(
            config_type="policies",
            entity_id=policy.policy_id,
            version=policy.version,
            tenant_id=tenant_id,
            operation="CREATE",
            payload=snapshot,
            actor=actor,
            actor_role=actor_role,
        )

        return policy

    async def get(self, id: str, tenant_id: str | None = None) -> Policy:
        policy = await self._repo.get_by_id_and_tenant(id, tenant_id=tenant_id)
        if not policy:
            raise PolicyNotFound(f"Policy '{id}' not found")
        return policy

    async def get_by_policy_id(self, policy_id: str, tenant_id: str | None = None) -> Policy:
        policy = await self._repo.get_by_policy_id(policy_id, tenant_id=tenant_id)
        if not policy:
            raise PolicyNotFound(f"Policy '{policy_id}' not found")
        return policy

    async def list(
        self,
        *,
        q: str | None = None,
        is_enabled: bool | None = None,
        tenant_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Policy], int]:
        skip = (page - 1) * page_size
        items, total = await self._repo.search(
            q=q, is_enabled=is_enabled, tenant_id=tenant_id, skip=skip, limit=page_size
        )
        return list(items), total

    async def update(
        self,
        id: str,
        data: PolicyUpdate,
        actor: str,
        actor_role: str | None,
        tenant_id: str | None = None,
    ) -> Policy:
        policy = await self.get(id, tenant_id=tenant_id)
        before = self._snapshot(policy)
        update_data: dict[str, Any] = data.model_dump(exclude_none=True)
        update_data.pop("tenant_id", None)
        reason = update_data.pop("reason", None)
        if "conditions" in update_data:
            update_data["conditions"] = [
                c.model_dump() if hasattr(c, "model_dump") else c for c in update_data["conditions"]
            ]
        update_data["updated_by"] = actor
        policy = await self._repo.update(policy, update_data)
        await self._repo.add_version(policy, actor, reason)
        snapshot = self._snapshot(policy)

        await self._audit.record(
            actor=actor,
            actor_role=actor_role,
            action=AuditAction.POLICY_UPDATED,
            resource_type="policy",
            resource_id=policy.policy_id,
            tenant_id=policy.tenant_id,
            version=policy.version,
            before_state=before,
            after_state=snapshot,
            reason=reason,
        )

        # Automatic lifecycle trigger: propagate update to M5
        await self._dist.trigger_propagation(
            config_type="policies",
            entity_id=policy.policy_id,
            version=policy.version,
            tenant_id=policy.tenant_id,
            operation="UPDATE",
            payload=snapshot,
            actor=actor,
            actor_role=actor_role,
        )

        return policy

    async def delete(
        self, id: str, actor: str, actor_role: str | None, tenant_id: str | None = None
    ) -> None:
        policy = await self.get(id, tenant_id=tenant_id)
        before = self._snapshot(policy)
        await self._repo.delete(policy)

        await self._audit.record(
            actor=actor,
            actor_role=actor_role,
            action=AuditAction.POLICY_DELETED,
            resource_type="policy",
            resource_id=policy.policy_id,
            tenant_id=policy.tenant_id,
            before_state=before,
        )

        # Automatic lifecycle trigger: propagate deletion to M5
        await self._dist.trigger_propagation(
            config_type="policies",
            entity_id=policy.policy_id,
            version=policy.version,
            tenant_id=policy.tenant_id,
            operation="DELETE",
            payload={"policy_id": policy.policy_id},
            actor=actor,
            actor_role=actor_role,
        )

    async def enable(
        self, id: str, actor: str, actor_role: str | None, tenant_id: str | None = None
    ) -> Policy:
        policy = await self.get(id, tenant_id=tenant_id)
        policy.is_enabled = True
        policy.updated_by = actor
        await self._repo._db.flush()
        snapshot = self._snapshot(policy)

        await self._audit.record(
            actor=actor,
            actor_role=actor_role,
            action=AuditAction.POLICY_ENABLED,
            resource_type="policy",
            resource_id=policy.policy_id,
            tenant_id=policy.tenant_id,
            after_state=snapshot,
        )

        await self._dist.trigger_propagation(
            config_type="policies",
            entity_id=policy.policy_id,
            version=policy.version,
            tenant_id=policy.tenant_id,
            operation="ENABLE",
            payload=snapshot,
            actor=actor,
            actor_role=actor_role,
        )

        return policy

    async def disable(
        self, id: str, actor: str, actor_role: str | None, tenant_id: str | None = None
    ) -> Policy:
        policy = await self.get(id, tenant_id=tenant_id)
        policy.is_enabled = False
        policy.updated_by = actor
        await self._repo._db.flush()
        snapshot = self._snapshot(policy)

        await self._audit.record(
            actor=actor,
            actor_role=actor_role,
            action=AuditAction.POLICY_DISABLED,
            resource_type="policy",
            resource_id=policy.policy_id,
            tenant_id=policy.tenant_id,
            after_state=snapshot,
        )

        await self._dist.trigger_propagation(
            config_type="policies",
            entity_id=policy.policy_id,
            version=policy.version,
            tenant_id=policy.tenant_id,
            operation="DISABLE",
            payload=snapshot,
            actor=actor,
            actor_role=actor_role,
        )

        return policy

    @staticmethod
    def _snapshot(p: Policy) -> dict[str, Any]:
        return {
            "policy_id": p.policy_id,
            "tenant_id": p.tenant_id,
            "name": p.name,
            "version": p.version,
            "priority": p.priority,
            "is_enabled": p.is_enabled,
            "conditions": p.conditions,
            "destinations": p.destinations,
        }
