"""Add per-product cold chain config and shipment limit snapshot columns (N3-62).

Revision ID: 20261020_32
Revises: 20261020_31
Create Date: 2026-10-19 21:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "20261020_32"
down_revision: str | Sequence[str] | None = "20261020_31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _application_role() -> str | None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text(
            "SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :role AND :role <> current_user"
        ),
        {"role": settings.DB_USER},
    ).scalar()
    return bind.dialect.identifier_preparer.quote(settings.DB_USER) if exists else None


def upgrade() -> None:
    # 1. Per-product cold chain configuration (shared catalog, admin-managed)
    op.create_table(
        "product_cold_chain_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("min_temp_celsius", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("max_temp_celsius", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("delay_minutes", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "min_temp_celsius < max_temp_celsius",
            name="ck_cold_chain_configs_temp_range",
        ),
        sa.CheckConstraint(
            "min_temp_celsius >= -50 AND max_temp_celsius <= 80",
            name="ck_cold_chain_configs_temp_bounds",
        ),
        sa.CheckConstraint(
            "delay_minutes >= 1 AND delay_minutes <= 1440",
            name="ck_cold_chain_configs_delay_range",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_cold_chain_configs_product_id_products",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["users.id"],
            name="fk_cold_chain_configs_updated_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", name="uq_cold_chain_configs_product"),
    )

    # 2. Guard the shared config like the product catalog: every authenticated
    #    session may read; only system_admin may write.
    op.execute("ALTER TABLE product_cold_chain_configs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE product_cold_chain_configs FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY cold_chain_configs_read_authenticated ON product_cold_chain_configs
        FOR SELECT
        USING (public.app_current_user_id() IS NOT NULL)
        """
    )
    op.execute(
        """
        CREATE POLICY cold_chain_configs_create_system_admin ON product_cold_chain_configs
        FOR INSERT
        WITH CHECK (public.app_current_role() = 'system_admin')
        """
    )
    op.execute(
        """
        CREATE POLICY cold_chain_configs_update_system_admin ON product_cold_chain_configs
        FOR UPDATE
        USING (public.app_current_role() = 'system_admin')
        WITH CHECK (public.app_current_role() = 'system_admin')
        """
    )
    op.execute(
        """
        CREATE POLICY cold_chain_configs_delete_system_admin ON product_cold_chain_configs
        FOR DELETE
        USING (public.app_current_role() = 'system_admin')
        """
    )

    app_role = _application_role()
    if app_role:
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON product_cold_chain_configs TO {app_role}"
        )

    # 3. Snapshot of the strictest limits frozen on each shipment (N3-62).
    #    NULL only for trips opened before this migration.
    op.add_column(
        "shipments",
        sa.Column(
            "cold_chain_min_temp_celsius",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "shipments",
        sa.Column(
            "cold_chain_max_temp_celsius",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "shipments",
        sa.Column("cold_chain_delay_minutes", sa.Integer(), nullable=True),
    )
    op.add_column(
        "shipments",
        sa.Column(
            "cold_chain_config_resolved_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.create_check_constraint(
        "ck_shipments_cold_chain_delay_range",
        "shipments",
        "cold_chain_delay_minutes IS NULL OR (cold_chain_delay_minutes >= 1 AND cold_chain_delay_minutes <= 1440)",
    )
    if app_role:
        op.execute(
            f"GRANT UPDATE (cold_chain_min_temp_celsius, cold_chain_max_temp_celsius, "
            f"cold_chain_delay_minutes, cold_chain_config_resolved_at, "
            f"effective_min_temp, effective_max_temp, effective_delay_minutes) ON shipments TO {app_role}"
        )


def downgrade() -> None:
    app_role = _application_role()
    if app_role:
        op.execute(f"REVOKE ALL ON product_cold_chain_configs FROM {app_role}")

    op.execute(
        "DROP POLICY IF EXISTS cold_chain_configs_delete_system_admin ON product_cold_chain_configs;"
    )
    op.execute(
        "DROP POLICY IF EXISTS cold_chain_configs_update_system_admin ON product_cold_chain_configs;"
    )
    op.execute(
        "DROP POLICY IF EXISTS cold_chain_configs_create_system_admin ON product_cold_chain_configs;"
    )
    op.execute(
        "DROP POLICY IF EXISTS cold_chain_configs_read_authenticated ON product_cold_chain_configs;"
    )
    op.execute("ALTER TABLE product_cold_chain_configs NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE product_cold_chain_configs DISABLE ROW LEVEL SECURITY")

    op.drop_constraint(
        "ck_shipments_cold_chain_delay_range", "shipments", type_="check"
    )
    op.drop_column("shipments", "cold_chain_config_resolved_at")
    op.drop_column("shipments", "cold_chain_delay_minutes")
    op.drop_column("shipments", "cold_chain_max_temp_celsius")
    op.drop_column("shipments", "cold_chain_min_temp_celsius")

    op.drop_table("product_cold_chain_configs")
