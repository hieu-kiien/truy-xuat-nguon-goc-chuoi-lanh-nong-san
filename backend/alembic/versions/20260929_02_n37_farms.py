"""Create organization-owned farms for N3-7.

Revision ID: 20260929_02
Revises: 20260929_01
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260929_02"
down_revision: str | None = "20260929_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "farms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("area_ha", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.CheckConstraint("area_ha > 0", name="ck_farms_area_positive"),
        sa.CheckConstraint(
            "latitude >= -90 AND latitude <= 90", name="ck_farms_latitude_range"
        ),
        sa.CheckConstraint(
            "longitude >= -180 AND longitude <= 180", name="ck_farms_longitude_range"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_farms_organization_id", "farms", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_farms_organization_id", table_name="farms")
    op.drop_table("farms")
