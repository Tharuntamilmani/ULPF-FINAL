"""Add tenants and distribution_target_states, align multi-tenancy schema.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-14 17:00:00.000000

"""

from __future__ import annotations

from datetime import datetime, timezone
import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ── 1. Create tenants table ────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)
    op.create_index("ix_tenants_status", "tenants", ["status"])

    # ── 2. Pre-seed default tenants for baseline operational support ───────────
    tenants_table = sa.table(
        "tenants",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("status", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(timezone.utc)
    op.bulk_insert(
        tenants_table,
        [
            {
                "id": "default-tenant-uuid",
                "name": "Default Tenant",
                "slug": "default",
                "status": "ACTIVE",
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "demo-tenant",
                "name": "Demo Tenant",
                "slug": "demo-tenant",
                "status": "ACTIVE",
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "default",
                "name": "Platform Default Tenant",
                "slug": "platform-default",
                "status": "ACTIVE",
                "created_at": now,
                "updated_at": now,
            },
        ],
    )

    # ── 3. Create distribution_target_states table ─────────────────────────────
    op.create_table(
        "distribution_target_states",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("distribution_id", sa.String(64), nullable=False),
        sa.Column(
            "config_version_id",
            sa.String(36),
            sa.ForeignKey("configuration_versions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("target_module", sa.String(16), nullable=False),
        sa.Column("config_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(128), nullable=True),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=True),
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ack_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("distribution_id", "target_module", name="uq_dist_target"),
    )
    op.create_index("ix_dist_target_status", "distribution_target_states", ["status"])
    op.create_index("ix_dist_target_distribution_id", "distribution_target_states", ["distribution_id"])
    op.create_index("ix_dist_target_module", "distribution_target_states", ["target_module"])
    op.create_index("ix_dist_target_tenant_id", "distribution_target_states", ["tenant_id"])
    op.create_index("ix_dist_target_correlation_id", "distribution_target_states", ["correlation_id"])

    # ── 4. Add tenant_id to users ──────────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    # ── 5. Add tenant_id to audit_logs ─────────────────────────────────────────
    op.add_column(
        "audit_logs",
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])

    # ── 6. Add tenant_id to parsers ────────────────────────────────────────────
    op.add_column(
        "parsers",
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_parsers_tenant_id", "parsers", ["tenant_id"])

    # ── 7. Add tenant_id to mappings ───────────────────────────────────────────
    op.add_column(
        "mappings",
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_mappings_tenant_id", "mappings", ["tenant_id"])

    # ── 8. Add tenant_id and composite constraints to policies ─────────────────
    op.add_column(
        "policies",
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            server_default="default-tenant-uuid",
        ),
    )
    op.drop_index("ix_policies_policy_id", table_name="policies")
    op.create_index("ix_policies_policy_id", "policies", ["policy_id"])
    op.create_index("ix_policies_tenant_id", "policies", ["tenant_id"])
    op.create_index("ix_policies_priority", "policies", ["priority"])
    op.create_unique_constraint("uq_tenant_policy", "policies", ["tenant_id", "policy_id"])

    # ── 9. Align sources constraints ───────────────────────────────────────────
    op.drop_index("ix_sources_source_id", table_name="sources")
    op.create_index("ix_sources_source_id", "sources", ["source_id"])
    op.create_unique_constraint("uq_tenant_source", "sources", ["tenant_id", "source_id"])
    op.create_foreign_key(
        "fk_sources_tenant_id",
        "sources",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_sources_tenant_id", "sources", type_="foreignkey")
    op.drop_constraint("uq_tenant_source", "sources", type_="unique")
    op.drop_index("ix_sources_source_id", table_name="sources")
    op.create_index("ix_sources_source_id", "sources", ["source_id"], unique=True)

    op.drop_constraint("uq_tenant_policy", "policies", type_="unique")
    op.drop_index("ix_policies_priority", table_name="policies")
    op.drop_index("ix_policies_tenant_id", table_name="policies")
    op.drop_index("ix_policies_policy_id", table_name="policies")
    op.create_index("ix_policies_policy_id", "policies", ["policy_id"], unique=True)
    op.drop_column("policies", "tenant_id")

    op.drop_index("ix_mappings_tenant_id", table_name="mappings")
    op.drop_column("mappings", "tenant_id")

    op.drop_index("ix_parsers_tenant_id", table_name="parsers")
    op.drop_column("parsers", "tenant_id")

    op.drop_index("ix_audit_logs_tenant_id", table_name="audit_logs")
    op.drop_column("audit_logs", "tenant_id")

    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_column("users", "tenant_id")

    op.drop_table("distribution_target_states")
    op.drop_table("tenants")
