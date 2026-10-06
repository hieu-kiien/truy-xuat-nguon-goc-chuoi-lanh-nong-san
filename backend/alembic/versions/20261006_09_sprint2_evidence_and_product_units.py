"""Use a database enum for shared product units.

Revision ID: 20261006_09
Revises: 20261006_08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

revision: str = "20261006_09"
down_revision: str | None = "20261006_08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


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


def upgrade() -> None:
    product_unit = postgresql.ENUM("kg", "tấn", "thùng", name="product_unit")
    product_unit.create(op.get_bind(), checkfirst=True)
    op.drop_constraint("ck_products_unit_supported", "products", type_="check")
    op.alter_column(
        "products",
        "unit",
        existing_type=sa.String(length=16),
        type_=product_unit,
        postgresql_using="unit::product_unit",
        existing_nullable=False,
    )
    op.execute(
        """
        CREATE POLICY products_update_system_admin ON products
        FOR UPDATE
        USING (public.app_current_role() = 'system_admin')
        WITH CHECK (public.app_current_role() = 'system_admin')
        """
    )

    op.create_index(
        "ix_lots_holder_product_harvested",
        "lots",
        ["current_holder_organization_id", "product_id", "harvested_on", "id"],
    )

    role = _application_role()
    if role:
        op.execute(f"GRANT UPDATE (name, unit) ON products TO {role}")


def downgrade() -> None:
    role = _application_role()
    if role:
        op.execute(f"REVOKE UPDATE (name, unit) ON products FROM {role}")

    op.drop_index("ix_lots_holder_product_harvested", table_name="lots")
    op.execute("DROP POLICY IF EXISTS products_update_system_admin ON products")
    product_unit = postgresql.ENUM("kg", "tấn", "thùng", name="product_unit")
    op.alter_column(
        "products",
        "unit",
        existing_type=product_unit,
        type_=sa.String(length=16),
        postgresql_using="unit::text",
        existing_nullable=False,
    )
    product_unit.drop(op.get_bind(), checkfirst=True)
    op.create_check_constraint(
        "ck_products_unit_supported",
        "products",
        "unit IN ('kg', 'tấn', 'thùng')",
    )
