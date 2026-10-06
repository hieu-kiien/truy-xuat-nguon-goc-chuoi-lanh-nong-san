"""Add the shared product catalog for harvest lots.

Revision ID: 20261006_06
Revises: 20261005_05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

revision: str = "20261006_06"
down_revision: str | None = "20261005_05"
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


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_products_name_nonblank"),
        sa.CheckConstraint(
            "unit IN ('kg', 'tấn', 'thùng')", name="ck_products_unit_supported"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_products_name_ci",
        "products",
        [sa.text("lower(name)")],
        unique=True,
    )

    op.execute("ALTER TABLE products ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY products_read_authenticated ON products
        FOR SELECT
        USING (public.app_current_user_id() IS NOT NULL)
        """
    )
    op.execute(
        """
        CREATE POLICY products_create_system_admin ON products
        FOR INSERT
        WITH CHECK (public.app_current_role() = 'system_admin')
        """
    )

    role = _application_role()
    if role:
        op.execute(f"GRANT SELECT, INSERT ON products TO {role}")
        op.execute(f"REVOKE UPDATE, DELETE ON products FROM {role}")


def downgrade() -> None:
    role = _application_role()
    if role:
        op.execute(f"REVOKE SELECT, INSERT ON products FROM {role}")

    op.execute("DROP POLICY IF EXISTS products_create_system_admin ON products")
    op.execute("DROP POLICY IF EXISTS products_read_authenticated ON products")
    op.execute("ALTER TABLE products NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE products DISABLE ROW LEVEL SECURITY")
    op.drop_index("uq_products_name_ci", table_name="products")
    op.drop_table("products")
