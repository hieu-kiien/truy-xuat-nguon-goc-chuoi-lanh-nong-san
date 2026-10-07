"""Create the shared product catalog for S-07.

Revision ID: 20261007_06
Revises: 20261005_05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

revision: str = "20261007_06"
down_revision: str | None = "20261005_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_application_role() -> bool:
    return bool(
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM pg_catalog.pg_roles "
                "WHERE rolname = :role AND :role <> current_user"
            ),
            {"role": settings.DB_USER},
        )
        .scalar()
    )


def _application_role() -> str:
    return op.get_bind().dialect.identifier_preparer.quote(settings.DB_USER)


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_products_name_nonblank"),
        sa.CheckConstraint("price >= 0", name="ck_products_price_positive"),
        sa.CheckConstraint(
            "unit IN ('kg', 'tấn', 'thùng')", name="ck_products_unit_allowed"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_product_name"),
    )

    if _has_application_role():
        role = _application_role()
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON products TO {role}")


def downgrade() -> None:
    if _has_application_role():
        role = _application_role()
        op.execute(f"REVOKE SELECT, INSERT, UPDATE, DELETE ON products FROM {role}")
    op.drop_table("products")
