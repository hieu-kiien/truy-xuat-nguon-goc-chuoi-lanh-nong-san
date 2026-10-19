"""Add temperature_readings table with cold chain RLS policies and append-only trigger (N3-60, S-41).

Revision ID: 20261018_27
Revises: 20261016_26
Create Date: 2026-10-18 21:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "20261018_27"
down_revision: str | Sequence[str] | None = "20261016_26"
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
    # 1. Create temperature_readings table
    op.create_table(
        "temperature_readings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("shipment_id", sa.UUID(), nullable=False),
        sa.Column("container_code", sa.String(length=64), nullable=False),
        sa.Column(
            "temperature_celsius",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["shipments.id"],
            name="fk_temperature_readings_shipment_id_shipments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shipment_id", "recorded_at", name="uq_shipment_reading_time"
        ),
    )
    op.create_index(
        "ix_temperature_readings_shipment_id",
        "temperature_readings",
        ["shipment_id"],
        unique=False,
    )
    op.create_index(
        "ix_temperature_readings_container_code",
        "temperature_readings",
        ["container_code"],
        unique=False,
    )
    op.create_index(
        "ix_temperature_readings_recorded_at",
        "temperature_readings",
        ["recorded_at"],
        unique=False,
    )

    # 2. Enable Row-Level Security
    op.execute("ALTER TABLE temperature_readings ENABLE ROW LEVEL SECURITY;")

    # 3. Create RLS Policies
    op.execute(
        """
        CREATE POLICY temperature_readings_tenant_select ON temperature_readings
        FOR SELECT USING (
            public.app_current_role() IN ('inspector', 'system_admin')
            OR EXISTS (
                SELECT 1 FROM public.shipments AS s
                WHERE s.id = temperature_readings.shipment_id
                  AND s.organization_id = public.app_current_organization_id()
            )
            OR EXISTS (
                SELECT 1 FROM public.shipment_lots AS sl
                JOIN public.lots AS l ON l.id = sl.lot_id
                WHERE sl.shipment_id = temperature_readings.shipment_id
                  AND l.current_holder_organization_id = public.app_current_organization_id()
            )
        );
        """
    )

    op.execute(
        """
        CREATE POLICY temperature_readings_tenant_insert ON temperature_readings
        FOR INSERT WITH CHECK (
            public.app_current_role() = 'system_admin'
            OR EXISTS (
                SELECT 1 FROM public.shipments AS s
                WHERE s.id = temperature_readings.shipment_id
                  AND s.organization_id = public.app_current_organization_id()
            )
        );
        """
    )

    # 4. Immutability Trigger (append-only)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_temperature_readings_append_only()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Dữ liệu đo nhiệt độ chuỗi lạnh là bất biến (append-only), không được phép sửa hoặc xóa.';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_temperature_readings_immutable
        BEFORE UPDATE OR DELETE ON temperature_readings
        FOR EACH ROW EXECUTE FUNCTION trg_temperature_readings_append_only();
        """
    )

    # 5. Role Grants
    app_role = _application_role()
    if app_role:
        op.execute(f"GRANT SELECT, INSERT ON temperature_readings TO {app_role};")


def downgrade() -> None:
    app_role = _application_role()
    if app_role:
        op.execute(f"REVOKE ALL ON temperature_readings FROM {app_role};")

    op.execute(
        "DROP TRIGGER IF EXISTS trg_temperature_readings_immutable ON temperature_readings;"
    )
    op.execute("DROP FUNCTION IF EXISTS trg_temperature_readings_append_only();")
    op.execute(
        "DROP POLICY IF EXISTS temperature_readings_tenant_insert ON temperature_readings;"
    )
    op.execute(
        "DROP POLICY IF EXISTS temperature_readings_tenant_select ON temperature_readings;"
    )
    op.drop_table("temperature_readings")
