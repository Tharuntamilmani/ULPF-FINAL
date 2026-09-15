"""
Standalone migration script — creates all M6 tables directly using psycopg2.
Use this inside Docker when alembic asyncio has DNS issues.
Run: python scripts/migrate.py
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import psycopg2

host = os.environ.get("POSTGRES_HOST", "postgres")
port = os.environ.get("POSTGRES_PORT", "5432")
db   = os.environ.get("POSTGRES_DB",   "m6_control_plane")
user = os.environ.get("POSTGRES_USER", "m6user")
pwd  = os.environ.get("POSTGRES_PASSWORD", "")

print(f"Connecting to PostgreSQL at {host}:{port}/{db} as {user}...")
conn = psycopg2.connect(host=host, port=port, dbname=db, user=user, password=pwd)
conn.autocommit = True
cur = conn.cursor()

print("Creating extension pgcrypto...")
cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

TABLES = [
    """
    CREATE TABLE IF NOT EXISTS roles (
        id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
        name VARCHAR(64) NOT NULL UNIQUE,
        description VARCHAR(255) NOT NULL DEFAULT '',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """
    CREATE TABLE IF NOT EXISTS users (
        id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
        username VARCHAR(64) NOT NULL UNIQUE,
        email VARCHAR(255) NOT NULL UNIQUE,
        hashed_password VARCHAR(255) NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT true,
        is_superuser BOOLEAN NOT NULL DEFAULT false,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """
    CREATE TABLE IF NOT EXISTS user_roles (
        user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role_id VARCHAR(36) NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
        PRIMARY KEY (user_id, role_id)
    )""",
    """
    CREATE TABLE IF NOT EXISTS sources (
        id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
        source_id VARCHAR(128) NOT NULL UNIQUE,
        tenant_id VARCHAR(128) NOT NULL DEFAULT 'default',
        name VARCHAR(255) NOT NULL,
        vendor VARCHAR(128) NOT NULL,
        product VARCHAR(128) NOT NULL,
        source_type VARCHAR(64) NOT NULL,
        protocol VARCHAR(64) NOT NULL,
        transport VARCHAR(32) NOT NULL,
        port INTEGER,
        zone VARCHAR(64),
        status VARCHAR(32) NOT NULL DEFAULT 'active',
        parser_id VARCHAR(128),
        description TEXT,
        tags TEXT,
        created_by VARCHAR(128),
        updated_by VARCHAR(128),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """
    CREATE TABLE IF NOT EXISTS parsers (
        id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
        parser_id VARCHAR(128) NOT NULL UNIQUE,
        name VARCHAR(255) NOT NULL,
        vendor VARCHAR(128) NOT NULL,
        product VARCHAR(128) NOT NULL,
        format VARCHAR(64) NOT NULL,
        version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
        status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
        description TEXT,
        tags TEXT,
        created_by VARCHAR(128),
        updated_by VARCHAR(128),
        approved_by VARCHAR(128),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """
    CREATE TABLE IF NOT EXISTS parser_versions (
        id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
        parser_id VARCHAR(36) NOT NULL REFERENCES parsers(id) ON DELETE CASCADE,
        version VARCHAR(32) NOT NULL,
        status VARCHAR(32) NOT NULL,
        changed_by VARCHAR(128),
        reason TEXT,
        snapshot JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """
    CREATE TABLE IF NOT EXISTS schemas (
        id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
        name VARCHAR(128) NOT NULL,
        description TEXT,
        created_by VARCHAR(128),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """
    CREATE TABLE IF NOT EXISTS schema_versions (
        id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
        schema_id VARCHAR(36) NOT NULL REFERENCES schemas(id) ON DELETE CASCADE,
        version VARCHAR(32) NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'active',
        json_schema JSONB NOT NULL,
        changelog TEXT,
        created_by VARCHAR(128),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """
    CREATE TABLE IF NOT EXISTS mappings (
        id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
        mapping_id VARCHAR(128) NOT NULL UNIQUE,
        name VARCHAR(255) NOT NULL,
        source_format VARCHAR(128) NOT NULL,
        target_schema VARCHAR(128) NOT NULL,
        target_version VARCHAR(32) NOT NULL,
        version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
        fields JSONB NOT NULL,
        description TEXT,
        is_active BOOLEAN NOT NULL DEFAULT true,
        created_by VARCHAR(128),
        updated_by VARCHAR(128),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """
    CREATE TABLE IF NOT EXISTS mapping_versions (
        id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
        mapping_id VARCHAR(36) NOT NULL REFERENCES mappings(id) ON DELETE CASCADE,
        version VARCHAR(32) NOT NULL,
        fields_snapshot JSONB NOT NULL,
        changed_by VARCHAR(128),
        reason TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """
    CREATE TABLE IF NOT EXISTS policies (
        id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
        policy_id VARCHAR(128) NOT NULL UNIQUE,
        name VARCHAR(255) NOT NULL,
        version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
        priority INTEGER NOT NULL DEFAULT 50,
        conditions JSONB NOT NULL DEFAULT '[]',
        destinations JSONB NOT NULL DEFAULT '[]',
        is_enabled BOOLEAN NOT NULL DEFAULT true,
        description TEXT,
        created_by VARCHAR(128),
        updated_by VARCHAR(128),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """
    CREATE TABLE IF NOT EXISTS policy_versions (
        id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
        policy_id VARCHAR(36) NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
        version VARCHAR(32) NOT NULL,
        conditions_snapshot JSONB NOT NULL,
        destinations_snapshot JSONB NOT NULL,
        changed_by VARCHAR(128),
        reason TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """
    CREATE TABLE IF NOT EXISTS services (
        id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
        service_key VARCHAR(64) NOT NULL UNIQUE,
        name VARCHAR(128) NOT NULL,
        service_type VARCHAR(32) NOT NULL,
        base_url VARCHAR(512),
        description TEXT,
        is_critical BOOLEAN NOT NULL DEFAULT false,
        is_enabled BOOLEAN NOT NULL DEFAULT true,
        last_status VARCHAR(32) NOT NULL DEFAULT 'UNKNOWN',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """
    CREATE TABLE IF NOT EXISTS configuration_versions (
        id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
        version BIGINT NOT NULL,
        config_key VARCHAR(128) NOT NULL,
        payload JSONB NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'pending',
        error_message TEXT,
        distributed_by VARCHAR(128),
        redis_key VARCHAR(256),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
        timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
        actor VARCHAR(128) NOT NULL,
        actor_role VARCHAR(64),
        action VARCHAR(64) NOT NULL,
        resource_type VARCHAR(64) NOT NULL,
        resource_id VARCHAR(256),
        version VARCHAR(32),
        before_state JSONB,
        after_state JSONB,
        reason TEXT,
        result VARCHAR(16) NOT NULL DEFAULT 'SUCCESS',
        request_id VARCHAR(64),
        extra JSONB
    )""",
    """
    CREATE TABLE IF NOT EXISTS replay_operations (
        id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
        event_id VARCHAR(256) NOT NULL,
        source VARCHAR(128),
        reason TEXT,
        requested_by VARCHAR(128) NOT NULL,
        requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        status VARCHAR(32) NOT NULL DEFAULT 'REQUESTED',
        error_message TEXT,
        completed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_sources_source_id ON sources(source_id)",
    "CREATE INDEX IF NOT EXISTS ix_sources_tenant_id ON sources(tenant_id)",
    "CREATE INDEX IF NOT EXISTS ix_parsers_parser_id ON parsers(parser_id)",
    "CREATE INDEX IF NOT EXISTS ix_parsers_status ON parsers(status)",
    "CREATE INDEX IF NOT EXISTS ix_parser_versions_parser_id ON parser_versions(parser_id)",
    "CREATE INDEX IF NOT EXISTS ix_schemas_name ON schemas(name)",
    "CREATE INDEX IF NOT EXISTS ix_schema_versions_schema_id ON schema_versions(schema_id)",
    "CREATE INDEX IF NOT EXISTS ix_mappings_mapping_id ON mappings(mapping_id)",
    "CREATE INDEX IF NOT EXISTS ix_mapping_versions_mapping_id ON mapping_versions(mapping_id)",
    "CREATE INDEX IF NOT EXISTS ix_policies_policy_id ON policies(policy_id)",
    "CREATE INDEX IF NOT EXISTS ix_policy_versions_policy_id ON policy_versions(policy_id)",
    "CREATE INDEX IF NOT EXISTS ix_services_service_key ON services(service_key)",
    "CREATE INDEX IF NOT EXISTS ix_configuration_versions_config_key ON configuration_versions(config_key)",
    "CREATE INDEX IF NOT EXISTS ix_configuration_versions_version ON configuration_versions(version)",
    "CREATE INDEX IF NOT EXISTS ix_audit_logs_actor ON audit_logs(actor)",
    "CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs(action)",
    "CREATE INDEX IF NOT EXISTS ix_audit_logs_timestamp ON audit_logs(timestamp)",
    "CREATE INDEX IF NOT EXISTS ix_audit_logs_resource ON audit_logs(resource_type, resource_id)",
    "CREATE INDEX IF NOT EXISTS ix_replay_operations_event_id ON replay_operations(event_id)",
    "CREATE INDEX IF NOT EXISTS ix_replay_operations_status ON replay_operations(status)",
]

print(f"Creating {len(TABLES)} tables...")
for sql in TABLES:
    table_name = [l.strip() for l in sql.split('\n') if 'TABLE IF NOT EXISTS' in l][0].split()[-1]
    cur.execute(sql)
    print(f"  OK: {table_name}")

print(f"\nCreating {len(INDEXES)} indexes...")
for sql in INDEXES:
    cur.execute(sql)

cur.close()
conn.close()
print("\nAll tables and indexes created successfully!")
print("Database is ready.")
