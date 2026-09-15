"""
Configuration Distribution Service with Transactional Outbox.

Target module mapping:
  Sources  → M1
  Parsers  → M2
  Schemas  → M3
  Mappings → M3
  Policies → M5

Architecture:
  PostgreSQL (source of truth)
      ↓ DB Transaction
      ↓ 1. Mutate configuration
      ↓ 2. Persist ConfigurationVersion & DistributionTargetState (PENDING)
      ↓ 3. Commit
      ↓ Dispatcher
      ↓ 4. Push versioned event to M1/M2/M3/M5
      ↓ 5. Receive & validate ACK
      ↓ 6. Transition state: ACKNOWLEDGED / FAILED
      ↓ 7. Record AuditLog
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import jsonschema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.audit.audit_service import AuditService
from backend.app.core.config import get_settings
from backend.app.core.exceptions import VersionMismatchError, WrongModuleAckError
from backend.app.core.logging import get_logger
from backend.app.integrations.m1_client import get_m1_client
from backend.app.integrations.m2_client import get_m2_client
from backend.app.integrations.m3_client import get_m3_client
from backend.app.integrations.m4_client import get_m4_client
from backend.app.integrations.m5_client import get_m5_client
from backend.app.integrations.module_client import ModuleClient
from backend.app.integrations.redis_client import get_redis_client
from backend.app.models.audit_log import AuditAction
from backend.app.models.config_distribution import DistributionStatus, DistributionTargetState
from backend.app.models.config_version import ConfigDistributionStatus, ConfigurationVersion
from backend.app.models.mapping import Mapping
from backend.app.models.parser import Parser, ParserStatus
from backend.app.models.policy import Policy
from backend.app.models.schema import Schema, SchemaStatus
from backend.app.models.source import Source, SourceStatus
from backend.app.repositories.distribution_repo import DistributionRepository

logger = get_logger("config_service")

_REDIS_NS = "config"
_VERSION_KEY = f"{_REDIS_NS}:version"
_UPDATED_AT_KEY = f"{_REDIS_NS}:updated_at"

# Contracts path
CONTRACTS_DIR = Path(__file__).resolve().parents[3] / "contracts"


def _load_schema(schema_name: str) -> dict[str, Any]:
    schema_path = CONTRACTS_DIR / schema_name
    with open(schema_path, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


try:
    CONFIG_EVENT_SCHEMA = _load_schema("config_event.schema.json")
    CONFIG_ACK_SCHEMA = _load_schema("config_ack.schema.json")
except Exception as exc:
    logger.warning("Could not load contracts schemas at startup", error=str(exc))
    CONFIG_EVENT_SCHEMA = {}
    CONFIG_ACK_SCHEMA = {}


class ConfigDistributionService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._settings = get_settings()
        self._dist_repo = DistributionRepository(db)
        self._audit = AuditService(db)

    # ── Target Module Mapping ──────────────────────────────────────────────────

    @staticmethod
    def get_target_modules(config_type: str) -> list[str]:
        mapping = {
            "sources": ["M1"],
            "parsers": ["M2"],
            "schemas": ["M3"],
            "mappings": ["M3"],
            "policies": ["M5"],
        }
        return mapping.get(config_type, [])

    def _get_client_for_module(self, module: str) -> ModuleClient | None:
        clients: dict[str, Any] = {
            "M1": get_m1_client,
            "M2": get_m2_client,
            "M3": get_m3_client,
            "M4": get_m4_client,
            "M5": get_m5_client,
        }
        getter = clients.get(module)
        return getter() if getter else None

    # ── Transactional Outbox: Create Event & Target Records ────────────────────

    async def create_outbox_event(
        self,
        *,
        config_type: str,
        entity_id: str | None,
        version: str,
        tenant_id: str | None,
        operation: str,
        payload: dict[str, Any],
        actor: str,
        actor_role: str | None,
        correlation_id: str | None = None,
    ) -> list[DistributionTargetState]:
        """
        Creates ConfigurationVersion and DistributionTargetState records inside DB transaction.
        Must be committed by the caller transaction.
        """
        distribution_id = str(uuid.uuid4())
        cid = correlation_id or str(uuid.uuid4())
        int_version = int(time.time_ns() // 1_000_000)

        # 1. Persist ConfigurationVersion
        cv = ConfigurationVersion(
            version=int_version,
            config_key=config_type,
            payload=payload,
            status=ConfigDistributionStatus.PENDING,
            distributed_by=actor,
            redis_key=f"{_REDIS_NS}:{config_type}",
        )
        self._db.add(cv)
        await self._db.flush()

        # 2. Determine target modules
        target_modules = self.get_target_modules(config_type)
        targets: list[DistributionTargetState] = []

        # 3. Create versioned event
        event = {
            "schema_version": "1.0.0",
            "distribution_id": distribution_id,
            "config_type": config_type,
            "entity_id": entity_id,
            "version": version,
            "tenant_id": tenant_id,
            "operation": operation,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
            "correlation_id": cid,
        }

        # Validate event contract against JSON schema
        if CONFIG_EVENT_SCHEMA:
            try:
                jsonschema.validate(event, CONFIG_EVENT_SCHEMA)
            except jsonschema.ValidationError as val_err:
                logger.error("Configuration event validation failed", error=str(val_err))
                raise ValueError(
                    f"Invalid configuration event contract: {val_err.message}"
                ) from val_err

        # 4. Create DistributionTargetState for each module
        for mod in target_modules:
            target_state = DistributionTargetState(
                distribution_id=distribution_id,
                config_version_id=cv.id,
                target_module=mod,
                config_type=config_type,
                entity_id=entity_id,
                version=version,
                tenant_id=tenant_id,
                operation=operation,
                payload=event,
                status=DistributionStatus.PENDING,
                correlation_id=cid,
            )
            self._db.add(target_state)
            targets.append(target_state)

        await self._db.flush()
        return targets

    # ── Automated Dispatch With Bounded Retry ─────────────────────────────────

    async def dispatch_targets(
        self,
        targets: list[DistributionTargetState],
        actor: str,
        actor_role: str | None,
    ) -> list[DistributionTargetState]:
        """
        Dispatches pending target records to modules with bounded retry (max 3, exp backoff max 10s).
        """
        for target in targets:
            await self._dispatch_single_target(target, actor, actor_role)
        return targets

    async def _dispatch_single_target(
        self,
        target: DistributionTargetState,
        actor: str,
        actor_role: str | None,
    ) -> DistributionTargetState:
        client = self._get_client_for_module(target.target_module)
        if not client:
            target.status = DistributionStatus.FAILED
            target.error_message = f"No client available for module {target.target_module}"
            await self._db.flush()
            return target

        target.status = DistributionStatus.SENT
        target.sent_at = datetime.now(UTC)
        await self._db.flush()

        # Bounded retry: max 3 attempts with exponential backoff (capped at 10s)
        max_attempts = target.max_retries
        last_error = None

        for attempt in range(1, max_attempts + 1):
            target.retry_count = attempt
            try:
                ack = await client.push_configuration(target.payload)

                # Validate ACK schema
                if CONFIG_ACK_SCHEMA:
                    try:
                        jsonschema.validate(ack, CONFIG_ACK_SCHEMA)
                    except jsonschema.ValidationError as ack_err:
                        logger.warning("ACK failed schema validation", error=str(ack_err))

                status_str = ack.get("status")
                if status_str == "APPLIED":
                    target.status = DistributionStatus.ACKNOWLEDGED
                    target.ack_at = datetime.now(UTC)
                    target.error_message = None
                    await self._db.flush()

                    await self._audit.record(
                        actor=actor,
                        actor_role=actor_role,
                        action=AuditAction.CONFIGURATION_ACKNOWLEDGED,
                        resource_type="config_distribution",
                        resource_id=target.distribution_id,
                        tenant_id=target.tenant_id,
                        after_state={"module": target.target_module, "status": "ACKNOWLEDGED"},
                    )
                    return target
                else:
                    # Explicit module rejection
                    target.status = DistributionStatus.FAILED
                    target.error_message = (
                        ack.get("error")
                        or f"Module rejected configuration with status {status_str}"
                    )
                    await self._db.flush()
                    return target

            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Target dispatch attempt failed",
                    module=target.target_module,
                    attempt=attempt,
                    error=last_error,
                )
                if attempt < max_attempts:
                    backoff = min(10.0, 1.0 * (2 ** (attempt - 1)))
                    await asyncio.sleep(backoff)

        # Retries exhausted
        target.status = DistributionStatus.FAILED
        target.error_message = f"Exhausted {max_attempts} attempts: {last_error}"
        await self._db.flush()

        await self._audit.record(
            actor=actor,
            actor_role=actor_role,
            action=AuditAction.CONFIGURATION_FAILED,
            resource_type="config_distribution",
            resource_id=target.distribution_id,
            tenant_id=target.tenant_id,
            after_state={
                "module": target.target_module,
                "status": "FAILED",
                "error": target.error_message,
            },
        )
        return target

    # ── Process Inbound Acknowledgement (Idempotent) ──────────────────────────

    async def process_ack(
        self,
        *,
        distribution_id: str,
        config_id: str,
        version: str,
        module: str,
        status: str,
        correlation_id: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        """
        Process inbound ACK from downstream module.
        Enforces idempotency, version consistency, and module match.
        """
        ack_payload = {
            "distribution_id": distribution_id,
            "config_id": config_id,
            "version": version,
            "module": module,
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
            "correlation_id": correlation_id,
            "error": error,
        }

        if CONFIG_ACK_SCHEMA:
            try:
                jsonschema.validate(ack_payload, CONFIG_ACK_SCHEMA)
            except jsonschema.ValidationError as e:
                return {"success": False, "reason": f"Malformed ACK payload: {e.message}"}

        target = await self._dist_repo.get_by_distribution_and_module(distribution_id, module)
        if not target:
            raise WrongModuleAckError(
                f"Unknown distribution '{distribution_id}' for module '{module}'"
            )

        # Stale ACK / version mismatch check
        if str(target.version) != str(version):
            raise VersionMismatchError(
                f"Version mismatch: target is {target.version}, ACK was {version}"
            )

        # Idempotency: duplicate ACK is harmless
        if target.status == DistributionStatus.ACKNOWLEDGED and status == "APPLIED":
            return {
                "success": True,
                "status": "ACKNOWLEDGED",
                "duplicate": True,
                "distribution_id": distribution_id,
            }

        dist_status = (
            DistributionStatus.ACKNOWLEDGED if status == "APPLIED" else DistributionStatus.FAILED
        )
        target.status = dist_status
        target.ack_at = datetime.now(UTC)
        if error:
            target.error_message = error

        await self._db.flush()
        return {"success": True, "status": dist_status.value, "distribution_id": distribution_id}

    dispatch_outbox_events = dispatch_targets

    # ── Query Distribution Status ─────────────────────────────────────────────

    async def get_distribution_status(self, distribution_id: str) -> dict[str, Any]:
        targets = await self._dist_repo.list_by_distribution_id(distribution_id)
        if not targets:
            return {"distribution_id": distribution_id, "found": False, "targets": []}

        all_acked = all(t.status == DistributionStatus.ACKNOWLEDGED for t in targets)
        any_failed = any(t.status == DistributionStatus.FAILED for t in targets)

        overall = "ACKNOWLEDGED" if all_acked else ("FAILED" if any_failed else "PENDING")
        return {
            "distribution_id": distribution_id,
            "found": True,
            "overall_status": overall,
            "targets": [
                {
                    "module": t.target_module,
                    "status": t.status.value,
                    "version": t.version,
                    "sent_at": t.sent_at.isoformat() if t.sent_at else None,
                    "ack_at": t.ack_at.isoformat() if t.ack_at else None,
                    "retry_count": t.retry_count,
                    "error": t.error_message,
                }
                for t in targets
            ],
        }

    # ── Automated Propagation Hook (Called by Registries) ─────────────────────

    async def trigger_propagation(
        self,
        *,
        config_type: str,
        entity_id: str | None,
        version: str,
        tenant_id: str | None,
        operation: str,
        payload: dict[str, Any],
        actor: str,
        actor_role: str | None,
    ) -> list[DistributionTargetState]:
        """Atomically stages outbox event and immediately initiates dispatch."""
        targets = await self.create_outbox_event(
            config_type=config_type,
            entity_id=entity_id,
            version=version,
            tenant_id=tenant_id,
            operation=operation,
            payload=payload,
            actor=actor,
            actor_role=actor_role,
        )
        # Attempt immediate dispatch
        await self.dispatch_targets(targets, actor, actor_role)
        # Sync snapshot to Redis
        try:
            await self._sync_redis_snapshot(config_type, actor)
        except Exception as exc:
            logger.warning("Redis snapshot update failed", error=str(exc))
        return targets

    async def _sync_redis_snapshot(self, config_type: str, actor: str) -> None:
        try:
            redis = await get_redis_client()
            builder = getattr(self, f"_build_{config_type}", None)
            if builder:
                data = await builder()
                serialised = json.dumps(data, default=str)
                await redis.set(f"{_REDIS_NS}:{config_type}", serialised)
        except Exception:
            pass

    # ── Snapshot Builders for Redis ───────────────────────────────────────────

    async def _build_sources(self) -> list[dict[str, Any]]:
        stmt = select(Source).where(Source.status == SourceStatus.ACTIVE)
        rows = (await self._db.execute(stmt)).scalars().all()
        return [
            {
                "source_id": s.source_id,
                "tenant_id": s.tenant_id,
                "name": s.name,
                "vendor": s.vendor,
                "product": s.product,
                "type": s.source_type,
                "protocol": s.protocol,
                "transport": s.transport,
                "port": s.port,
                "zone": s.zone,
                "parser_id": s.parser_id,
            }
            for s in rows
        ]

    async def _build_parsers(self) -> list[dict[str, Any]]:
        stmt = select(Parser).where(Parser.status == ParserStatus.ACTIVE)
        rows = (await self._db.execute(stmt)).scalars().all()
        return [
            {
                "parser_id": p.parser_id,
                "tenant_id": p.tenant_id,
                "name": p.name,
                "vendor": p.vendor,
                "product": p.product,
                "format": p.format,
                "version": p.version,
            }
            for p in rows
        ]

    async def _build_schemas(self) -> dict[str, Any]:
        from sqlalchemy.orm import selectinload

        stmt = select(Schema).options(selectinload(Schema.versions))
        rows = (await self._db.execute(stmt)).scalars().all()
        result: dict[str, Any] = {}
        for schema in rows:
            result[schema.name] = {}
            for sv in schema.versions:
                if sv.status == SchemaStatus.ACTIVE:
                    result[schema.name][sv.version] = sv.json_schema
        return result

    async def _build_mappings(self) -> list[dict[str, Any]]:
        stmt = select(Mapping).where(Mapping.is_active.is_(True))
        rows = (await self._db.execute(stmt)).scalars().all()
        return [
            {
                "mapping_id": m.mapping_id,
                "tenant_id": m.tenant_id,
                "source_format": m.source_format,
                "target_schema": m.target_schema,
                "target_version": m.target_version,
                "version": m.version,
                "fields": m.fields,
            }
            for m in rows
        ]

    async def _build_policies(self) -> list[dict[str, Any]]:
        stmt = select(Policy).where(Policy.is_enabled.is_(True)).order_by(Policy.priority.desc())
        rows = (await self._db.execute(stmt)).scalars().all()
        return [
            {
                "policy_id": p.policy_id,
                "tenant_id": p.tenant_id,
                "name": p.name,
                "version": p.version,
                "priority": p.priority,
                "conditions": p.conditions,
                "destinations": p.destinations,
            }
            for p in rows
        ]

    async def get_current_config(self) -> dict[str, Any]:
        try:
            redis = await get_redis_client()
            keys = ["sources", "parsers", "schemas", "mappings", "policies"]
            result: dict[str, Any] = {}
            for key in keys:
                raw = await redis.get(f"{_REDIS_NS}:{key}")
                result[key] = json.loads(raw) if raw else None
            result["version"] = await redis.get(_VERSION_KEY)
            result["updated_at"] = await redis.get(_UPDATED_AT_KEY)
            return result
        except Exception as exc:
            logger.warning("Could not read config from Redis", error=str(exc))
            return {"error": str(exc), "available": False}

    async def get_config_version(self) -> int:
        try:
            redis = await get_redis_client()
            v = await redis.get(_VERSION_KEY)
            return int(v) if v else 0
        except Exception:
            return 0
