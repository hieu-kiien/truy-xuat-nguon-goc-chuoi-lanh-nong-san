"""Create organization-owned farms and row security for N3-7.

Revision ID: 20260929_03
Revises: 20260929_02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

revision: str = "20260929_03"
down_revision: str | None = "20260929_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_application_role() -> bool:
    bind = op.get_bind()
    return bool(
        bind.execute(
            sa.text(
                "SELECT 1 FROM pg_catalog.pg_roles "
                "WHERE rolname = :role AND :role <> current_user"
            ),
            {"role": settings.DB_USER},
        ).scalar()
    )


def _application_role() -> str:
    return op.get_bind().dialect.identifier_preparer.quote(settings.DB_USER)


def upgrade() -> None:
    op.create_table(
        "farms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("area_ha", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.CheckConstraint(
            "area_ha > 0 AND area_ha <> 'NaN'::numeric",
            name="ck_farms_area_positive",
        ),
        sa.CheckConstraint(
            "latitude >= -90 AND latitude <= 90", name="ck_farms_latitude_range"
        ),
        sa.CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="ck_farms_longitude_range",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_farms_organization_id", "farms", ["organization_id"])
    op.execute("ALTER TABLE farms ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY farms_organization_isolation ON farms
        USING (
            organization_id = NULLIF(
                current_setting('app.current_organization', true), ''
            )::uuid
        )
        WITH CHECK (
            organization_id = NULLIF(
                current_setting('app.current_organization', true), ''
            )::uuid
        )
        """)

    if _has_application_role():
        role = _application_role()
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON farms TO {role}")


def downgrade() -> None:
    if _has_application_role():
        role = _application_role()
        op.execute(f"REVOKE SELECT, INSERT, UPDATE ON farms FROM {role}")
    op.execute("DROP POLICY farms_organization_isolation ON farms")
    op.execute("ALTER TABLE farms NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE farms DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_farms_organization_id", table_name="farms")
    op.drop_table("farms")
