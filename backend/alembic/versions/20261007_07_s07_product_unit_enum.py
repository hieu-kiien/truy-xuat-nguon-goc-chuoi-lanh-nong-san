"""Store product units as a PostgreSQL enum for S-07.

Revision ID: 20261007_07
Revises: 20261007_06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261007_07"
down_revision: str | None = "20261007_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

product_unit = postgresql.ENUM(
    "kg",
    "tấn",
    "thùng",
    name="product_unit",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    product_unit.create(bind, checkfirst=True)
    op.drop_constraint("ck_products_unit_allowed", "products", type_="check")
    op.alter_column(
        "products",
        "unit",
        existing_type=sa.String(length=50),
        type_=product_unit,
        postgresql_using="unit::product_unit",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "products",
        "unit",
        existing_type=product_unit,
        type_=sa.String(length=50),
        postgresql_using="unit::text",
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_products_unit_allowed",
        "products",
        "unit IN ('kg', 'tấn', 'thùng')",
    )
    product_unit.drop(op.get_bind(), checkfirst=True)
