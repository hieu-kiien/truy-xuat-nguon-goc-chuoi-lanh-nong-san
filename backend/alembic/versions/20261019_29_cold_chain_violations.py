"""Add cold chain parameters to shipments and create cold_chain_violations table (N3-59, N3-61, N3-63).

Revision ID: 20261019_29
Revises: 20261019_28
Create Date: 2026-10-19 19:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "20261019_29"
down_revision: str | Sequence[str] | None = "20261019_28"
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
    # 1. Add cold chain threshold and telemetry tracking columns to shipments
    op.add_column(
        "shipments",
        sa.Column(
            "effective_min_temp",
            sa.Numeric(precision=5, scale=2),
            server_default=sa.text("2.00"),
            nullable=False,
        ),
    )
    op.add_column(
        "shipments",
        sa.Column(
            "effective_max_temp",
            sa.Numeric(precision=5, scale=2),
            server_default=sa.text("8.00"),
            nullable=False,
        ),
    )
    op.add_column(
        "shipments",
        sa.Column(
            "effective_delay_minutes",
            sa.Integer(),
            server_default=sa.text("30"),
            nullable=False,
        ),
    )
    op.add_column(
        "shipments",
        sa.Column(
            "effective_merge_gap_minutes",
            sa.Integer(),
            server_default=sa.text("5"),
            nullable=False,
        ),
    )
    op.add_column(
        "shipments",
        sa.Column(
            "last_reading_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_shipments_effective_temps",
        "shipments",
        "effective_min_temp < effective_max_temp",
    )
    op.create_check_constraint(
        "ck_shipments_effective_delay",
        "shipments",
        "effective_delay_minutes > 0",
    )
    op.create_check_constraint(
        "ck_shipments_effective_merge",
        "shipments",
        "effective_merge_gap_minutes >= 0",
    )

    # 2. Create cold_chain_violations table
    op.create_table(
        "cold_chain_violations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("shipment_id", sa.UUID(), nullable=False),
        sa.Column("violation_type", sa.String(length=24), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "duration_minutes",
            sa.Numeric(precision=8, scale=2),
            nullable=True,
        ),
        sa.Column(
            "peak_temperature_celsius",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column(
            "is_settled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "violation_type IN ('high_temp', 'low_temp')",
            name="ck_cold_chain_violations_type",
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["shipments.id"],
            name="fk_cold_chain_violations_shipment_id_shipments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shipment_id", "started_at", name="uq_violation_start"),
    )
    op.create_index(
        "ix_cold_chain_violations_shipment_id",
        "cold_chain_violations",
        ["shipment_id"],
        unique=False,
    )

    # 3. Enable RLS on cold_chain_violations
    op.execute("ALTER TABLE cold_chain_violations ENABLE ROW LEVEL SECURITY;")

    # 4. Create RLS Policies
    op.execute(
        """
        CREATE POLICY cold_chain_violations_tenant_select ON cold_chain_violations
        FOR SELECT USING (
            public.app_current_role() IN ('inspector', 'system_admin')
            OR EXISTS (
                SELECT 1 FROM public.shipments AS s
                WHERE s.id = cold_chain_violations.shipment_id
                  AND s.organization_id = public.app_current_organization_id()
            )
            OR EXISTS (
                SELECT 1 FROM public.shipment_lots AS sl
                JOIN public.lots AS l ON l.id = sl.lot_id
                WHERE sl.shipment_id = cold_chain_violations.shipment_id
                  AND l.current_holder_organization_id = public.app_current_organization_id()
            )
        );
        """
    )

    op.execute(
        """
        CREATE POLICY cold_chain_violations_tenant_insert ON cold_chain_violations
        FOR INSERT WITH CHECK (
            public.app_current_role() = 'system_admin'
            OR EXISTS (
                SELECT 1 FROM public.shipments AS s
                WHERE s.id = cold_chain_violations.shipment_id
                  AND s.organization_id = public.app_current_organization_id()
            )
        );
        """
    )

    op.execute(
        """
        CREATE POLICY cold_chain_violations_tenant_update ON cold_chain_violations
        FOR UPDATE USING (
            public.app_current_role() = 'system_admin'
            OR EXISTS (
                SELECT 1 FROM public.shipments AS s
                WHERE s.id = cold_chain_violations.shipment_id
                  AND s.organization_id = public.app_current_organization_id()
            )
        );
        """
    )

    # 5. Role Grants
    app_role = _application_role()
    if app_role:
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE ON cold_chain_violations TO {app_role};"
        )


def downgrade() -> None:
    app_role = _application_role()
    if app_role:
        op.execute(f"REVOKE ALL ON cold_chain_violations FROM {app_role};")

    op.execute(
        "DROP POLICY IF EXISTS cold_chain_violations_tenant_update ON cold_chain_violations;"
    )
    op.execute(
        "DROP POLICY IF EXISTS cold_chain_violations_tenant_insert ON cold_chain_violations;"
    )
    op.execute(
        "DROP POLICY IF EXISTS cold_chain_violations_tenant_select ON cold_chain_violations;"
    )
    op.drop_table("cold_chain_violations")

    op.drop_constraint("ck_shipments_effective_merge", "shipments", type_="check")
    op.drop_constraint("ck_shipments_effective_delay", "shipments", type_="check")
    op.drop_constraint("ck_shipments_effective_temps", "shipments", type_="check")
    op.drop_column("shipments", "last_reading_at")
    op.drop_column("shipments", "effective_merge_gap_minutes")
    op.drop_column("shipments", "effective_delay_minutes")
    op.drop_column("shipments", "effective_max_temp")
    op.drop_column("shipments", "effective_min_temp")
