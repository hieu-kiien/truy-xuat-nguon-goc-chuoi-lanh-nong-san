"""Add hourly aggregates for old temperature readings (N3-64, S-51).

Readings older than the retention window are folded into one row per hour. The
aggregate rows are written by the maintenance job and read by the shipment
readings route, so an old shipment keeps a readable series without keeping
every raw reading.

Revision ID: 20261021_40
Revises: 20261021_39
Create Date: 2026-10-21 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "20261021_40"
down_revision: str | Sequence[str] | None = "20261021_39"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _application_role() -> str | None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text(
            "SELECT 1 FROM pg_catalog.pg_roles "
            "WHERE rolname = :role AND :role <> current_user"
        ),
        {"role": settings.DB_USER},
    ).scalar()
    if not exists:
        return None
    return bind.dialect.identifier_preparer.quote(settings.DB_USER)


def _application_role_literal() -> str:
    """Return the application role name as a SQL string literal."""
    return "'" + settings.DB_USER.replace("'", "''") + "'"


def upgrade() -> None:
    op.create_table(
        "temperature_hourly_aggregates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("container_code", sa.String(length=64), nullable=False),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "reading_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("min_temperature_celsius", sa.Numeric(5, 2), nullable=True),
        sa.Column("max_temperature_celsius", sa.Numeric(5, 2), nullable=True),
        sa.Column("avg_temperature_celsius", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "reading_count >= 0", name="ck_temperature_hourly_aggregates_count"
        ),
        sa.CheckConstraint(
            "(reading_count = 0 AND min_temperature_celsius IS NULL "
            "AND max_temperature_celsius IS NULL "
            "AND avg_temperature_celsius IS NULL) "
            "OR (reading_count > 0 AND min_temperature_celsius IS NOT NULL "
            "AND max_temperature_celsius IS NOT NULL "
            "AND avg_temperature_celsius IS NOT NULL)",
            name="ck_temperature_hourly_aggregates_gap_marker",
        ),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shipment_id",
            "bucket_start",
            name="uq_temperature_hourly_aggregates_shipment_bucket",
        ),
    )
    op.create_index(
        "ix_temperature_hourly_aggregates_shipment_bucket",
        "temperature_hourly_aggregates",
        ["shipment_id", "bucket_start"],
    )

    op.execute("ALTER TABLE temperature_hourly_aggregates ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY temperature_hourly_aggregates_read_tenant_or_auditor
        ON temperature_hourly_aggregates
        FOR SELECT
        USING (
            EXISTS (
                SELECT 1 FROM public.shipments s
                WHERE s.id = temperature_hourly_aggregates.shipment_id
                  AND (
                      s.organization_id = public.app_current_organization_id()
                      OR public.app_current_role() IN ('inspector', 'system_admin')
                  )
            )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY temperature_hourly_aggregates_write_maintenance
        ON temperature_hourly_aggregates
        FOR INSERT
        WITH CHECK (
            current_user <> """
        + _application_role_literal()
        + """
            OR EXISTS (
                SELECT 1 FROM public.shipments s
                WHERE s.id = temperature_hourly_aggregates.shipment_id
                  AND s.organization_id = public.app_current_organization_id()
            )
        )
        """
    )

    role = _application_role()
    if role:
        op.execute(f"GRANT SELECT, INSERT ON temperature_hourly_aggregates TO {role}")
        op.execute(
            f"REVOKE UPDATE, DELETE ON temperature_hourly_aggregates FROM {role}"
        )


def downgrade() -> None:
    role = _application_role()
    if role:
        op.execute(
            f"REVOKE SELECT, INSERT ON temperature_hourly_aggregates FROM {role}"
        )

    op.execute(
        "DROP POLICY IF EXISTS temperature_hourly_aggregates_write_maintenance "
        "ON temperature_hourly_aggregates"
    )
    op.execute(
        "DROP POLICY IF EXISTS temperature_hourly_aggregates_read_tenant_or_auditor "
        "ON temperature_hourly_aggregates"
    )
    op.execute("ALTER TABLE temperature_hourly_aggregates DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_temperature_hourly_aggregates_shipment_bucket",
        table_name="temperature_hourly_aggregates",
    )
    op.drop_table("temperature_hourly_aggregates")
