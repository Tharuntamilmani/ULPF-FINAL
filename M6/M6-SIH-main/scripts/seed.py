"""
M6 Bootstrap Seed Script.

Seeds ONLY M6 control-plane data:
  - Roles (ADMINISTRATOR, PARSER_DEVELOPER, SECURITY_ANALYST, VIEWER)
  - Admin user
  - Source metadata
  - Parser metadata
  - UES schemas
  - Mappings
  - Policies
  - Service registry entries

Run: python scripts/seed.py
Requires DATABASE_URL and other env vars to be set (or .env present).
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[1]))

from dotenv import load_dotenv
load_dotenv()

# Validate critical env vars before imports trigger Settings validation
for var in ("SECRET_KEY", "ADMIN_PASSWORD", "POSTGRES_PASSWORD"):
    if not os.getenv(var):
        os.environ.setdefault("SECRET_KEY", "dev-seed-secret-key-32chars-min!!")
        os.environ.setdefault("ADMIN_PASSWORD", "Admin@12345")
        os.environ.setdefault("POSTGRES_PASSWORD", "postgres")

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from backend.app.core.config import get_settings
from backend.app.core.security import hash_password
from backend.app.models.user import Role, User, UserRole
from backend.app.models.source import Source, SourceStatus
from backend.app.models.parser import Parser, ParserStatus
from backend.app.models.schema import Schema, SchemaVersion, SchemaStatus
from backend.app.models.mapping import Mapping
from backend.app.models.policy import Policy
from backend.app.models.service import Service, ServiceType, ServiceStatus


ROLES = [
    ("ADMINISTRATOR",    "Full control over M6 control plane"),
    ("PARSER_DEVELOPER", "Parser and mapping management"),
    ("SECURITY_ANALYST", "View services, configs, and dashboards"),
    ("VIEWER",           "Read-only access"),
]

SOURCES = [
    {"source_id": "cisco-asa-fw-01", "name": "Edge Firewall (Cisco ASA)", "vendor": "Cisco", "product": "ASA",
     "source_type": "firewall", "protocol": "syslog", "transport": "udp", "port": 514, "zone": "dmz",
     "tenant_id": "demo-tenant", "parser_id": "parser-cisco-asa"},
    {"source_id": "paloalto-ngfw-01", "name": "Core NGFW (Palo Alto)", "vendor": "Palo Alto Networks", "product": "PAN-OS",
     "source_type": "firewall", "protocol": "syslog", "transport": "tcp", "port": 514, "zone": "core",
     "tenant_id": "demo-tenant", "parser_id": "parser-paloalto"},
    {"source_id": "windows-dc-01", "name": "Domain Controller (Windows)", "vendor": "Microsoft", "product": "Windows Server",
     "source_type": "server", "protocol": "winrm", "transport": "tcp", "port": 5985, "zone": "internal",
     "tenant_id": "demo-tenant", "parser_id": "parser-windows"},
    {"source_id": "linux-web-01", "name": "Web Server (Linux)", "vendor": "Linux", "product": "Ubuntu 22.04",
     "source_type": "server", "protocol": "syslog", "transport": "udp", "port": 514, "zone": "dmz",
     "tenant_id": "demo-tenant", "parser_id": "parser-linux"},
]

PARSERS = [
    {"parser_id": "parser-cisco-asa", "name": "Cisco ASA Parser", "vendor": "Cisco", "product": "ASA",
     "format": "syslog", "version": "1.0.0", "status": ParserStatus.ACTIVE},
    {"parser_id": "parser-paloalto", "name": "Palo Alto PAN-OS Parser", "vendor": "Palo Alto Networks", "product": "PAN-OS",
     "format": "syslog", "version": "1.0.0", "status": ParserStatus.ACTIVE},
    {"parser_id": "parser-windows", "name": "Windows Event Log Parser", "vendor": "Microsoft", "product": "Windows",
     "format": "evtx", "version": "1.0.0", "status": ParserStatus.ACTIVE},
    {"parser_id": "parser-linux", "name": "Linux Syslog Parser", "vendor": "Linux", "product": "Syslog",
     "format": "syslog", "version": "1.0.0", "status": ParserStatus.ACTIVE},
    {"parser_id": "parser-cisco-asa-v2", "name": "Cisco ASA Parser v2 (Draft)", "vendor": "Cisco", "product": "ASA",
     "format": "syslog", "version": "2.0.0", "status": ParserStatus.DRAFT},
]

UES_SCHEMA = {
    "$id": "ulpf:ues:v1.0.0",
    "title": "UniversalEventSchema",
    "type": "object",
    "required": ["event_id", "tenant_id", "timestamp", "event"],
    "properties": {
        "event_id": {"type": "string"},
        "tenant_id": {"type": "string"},
        "timestamp": {"type": "string"},
        "event": {"type": "object"},
        "source": {"type": "object"},
        "destination": {"type": "object"},
        "observer": {"type": "object"},
    }
}

MAPPINGS = [
    {"mapping_id": "cisco-asa-ues-v1", "name": "Cisco ASA → UES v1.0.0",
     "source_format": "cisco-asa", "target_schema": "ues", "target_version": "1.0.0", "version": "1.0.0",
     "fields": {"srcip": "source.ip", "dstip": "destination.ip", "srcport": "source.port",
                "dstport": "destination.port", "action": "event.action", "severity": "event.severity.label"}},
    {"mapping_id": "paloalto-ues-v1", "name": "Palo Alto → UES v1.0.0",
     "source_format": "pan-os", "target_schema": "ues", "target_version": "1.0.0", "version": "1.0.0",
     "fields": {"src": "source.ip", "dst": "destination.ip", "sport": "source.port",
                "dport": "destination.port", "action": "event.action"}},
]

POLICIES = [
    {"policy_id": "critical-security", "name": "Critical Security Events", "version": "1.0.0",
     "priority": 100, "is_enabled": True, "tenant_id": "default-tenant-uuid",
     "conditions": [{"field": "event.severity.value", "operator": ">=", "value": 7},
                    {"field": "security.is_security_event", "operator": "==", "value": True}],
     "destinations": ["siem", "data_lake", "ai_stream"]},
    {"policy_id": "high-severity", "name": "High Severity Events", "version": "1.0.0",
     "priority": 80, "is_enabled": True, "tenant_id": "default-tenant-uuid",
     "conditions": [{"field": "event.severity.value", "operator": ">=", "value": 5}],
     "destinations": ["siem", "data_lake"]},
    {"policy_id": "default-data-lake", "name": "Default Data Lake", "version": "1.0.0",
     "priority": 1, "is_enabled": True, "tenant_id": "default-tenant-uuid",
     "conditions": [],
     "destinations": ["data_lake"]},
]

SERVICES = [
    ("m1-ingestion",  "M1 Ingestion Service",  ServiceType.MODULE,         False),
    ("m2-parser",     "M2 Parser Service",      ServiceType.MODULE,         False),
    ("m3-normalizer", "M3 Normalizer Service",  ServiceType.MODULE,         False),
    ("m4-enrichment", "M4 Enrichment Service",  ServiceType.MODULE,         False),
    ("m5-delivery",   "M5 SIEM Delivery",       ServiceType.MODULE,         False),
    ("kafka",         "Apache Kafka",           ServiceType.INFRASTRUCTURE, True),
    ("minio",         "MinIO Object Storage",   ServiceType.INFRASTRUCTURE, False),
    ("opensearch",    "OpenSearch",             ServiceType.INFRASTRUCTURE, False),
    ("postgres",      "PostgreSQL",             ServiceType.INFRASTRUCTURE, True),
    ("redis",         "Redis",                  ServiceType.INFRASTRUCTURE, True),
    ("prometheus",    "Prometheus",             ServiceType.INFRASTRUCTURE, False),
    ("grafana",       "Grafana",                ServiceType.INFRASTRUCTURE, False),
]


async def seed(session: AsyncSession) -> None:
    settings = get_settings()
    print("\n=== ULPF M6 Seed Script ===\n")

    # ── Roles ──────────────────────────────────────────────────────────────────
    from sqlalchemy import select
    role_map: dict[str, Role] = {}
    for name, desc in ROLES:
        r = (await session.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
        if not r:
            r = Role(name=name, description=desc)
            session.add(r)
            await session.flush()
            print(f"  Role created: {name}")
        role_map[name] = r

    # ── Admin user ─────────────────────────────────────────────────────────────
    admin = (await session.execute(select(User).where(User.username == settings.admin_username))).scalar_one_or_none()
    if not admin:
        admin = User(
            username=settings.admin_username,
            email=settings.admin_email,
            hashed_password=hash_password(settings.admin_password),
            is_superuser=True,
        )
        session.add(admin)
        await session.flush()
        session.add(UserRole(user_id=admin.id, role_id=role_map["ADMINISTRATOR"].id))
        await session.flush()
        print(f"  Admin user created: {settings.admin_username}")

    # ── Sources ────────────────────────────────────────────────────────────────
    for s in SOURCES:
        exists = (await session.execute(select(Source).where(Source.source_id == s["source_id"]))).scalar_one_or_none()
        if not exists:
            session.add(Source(**s, created_by=settings.admin_username, updated_by=settings.admin_username))
            print(f"  Source created: {s['source_id']}")
    await session.flush()

    # ── Parsers ────────────────────────────────────────────────────────────────
    for p in PARSERS:
        exists = (await session.execute(select(Parser).where(Parser.parser_id == p["parser_id"]))).scalar_one_or_none()
        if not exists:
            session.add(Parser(**p, created_by=settings.admin_username, updated_by=settings.admin_username,
                               approved_by=settings.admin_username if p["status"] == ParserStatus.ACTIVE else None))
            print(f"  Parser created: {p['parser_id']} ({p['status'].value})")
    await session.flush()

    # ── Schemas ────────────────────────────────────────────────────────────────
    ues_schema = (await session.execute(select(Schema).where(Schema.name == "ues"))).scalar_one_or_none()
    if not ues_schema:
        ues_schema = Schema(name="ues", description="Universal Event Schema", created_by=settings.admin_username)
        session.add(ues_schema)
        await session.flush()
        for ver, schema_doc in [("1.0.0", UES_SCHEMA)]:
            session.add(SchemaVersion(schema_id=ues_schema.id, version=ver, json_schema=schema_doc,
                                      status=SchemaStatus.ACTIVE, created_by=settings.admin_username))
        await session.flush()
        print("  Schema created: ues v1.0.0")

    # ── Mappings ───────────────────────────────────────────────────────────────
    for m in MAPPINGS:
        exists = (await session.execute(select(Mapping).where(Mapping.mapping_id == m["mapping_id"]))).scalar_one_or_none()
        if not exists:
            session.add(Mapping(**m, created_by=settings.admin_username, updated_by=settings.admin_username))
            print(f"  Mapping created: {m['mapping_id']}")
    await session.flush()

    # ── Policies ───────────────────────────────────────────────────────────────
    for p in POLICIES:
        exists = (await session.execute(select(Policy).where(Policy.policy_id == p["policy_id"]))).scalar_one_or_none()
        if not exists:
            session.add(Policy(**p, created_by=settings.admin_username, updated_by=settings.admin_username))
            print(f"  Policy created: {p['policy_id']}")
    await session.flush()

    # ── Services ───────────────────────────────────────────────────────────────
    for key, name, stype, critical in SERVICES:
        exists = (await session.execute(select(Service).where(Service.service_key == key))).scalar_one_or_none()
        if not exists:
            session.add(Service(service_key=key, name=name, service_type=stype,
                                is_critical=critical, last_status=ServiceStatus.UNKNOWN))
            print(f"  Service registered: {key}")
    await session.flush()

    await session.commit()
    print("\nSeed complete.\n")


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
