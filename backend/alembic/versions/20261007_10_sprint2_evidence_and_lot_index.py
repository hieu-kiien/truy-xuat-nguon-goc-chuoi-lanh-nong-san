"""Add the holder/product lot index and guard the shared product catalog."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261007_10"
down_revision: str | None = "20261007_09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_lots_holder_product_harvested",
        "lots",
        ["current_holder_organization_id", "product_id", "harvested_on", "id"],
    )
    op.create_index(
        "uq_products_name_ci",
        "products",
        [sa.text("lower(name)")],
        unique=True,
    )

    op.execute("ALTER TABLE products ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE products FORCE ROW LEVEL SECURITY")
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
    op.execute(
        """
        CREATE POLICY products_update_system_admin ON products
        FOR UPDATE
        USING (public.app_current_role() = 'system_admin')
        WITH CHECK (public.app_current_role() = 'system_admin')
        """
    )
    op.execute(
        """
        CREATE POLICY products_delete_system_admin ON products
        FOR DELETE
        USING (public.app_current_role() = 'system_admin')
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS products_delete_system_admin ON products")
    op.execute("DROP POLICY IF EXISTS products_update_system_admin ON products")
    op.execute("DROP POLICY IF EXISTS products_create_system_admin ON products")
    op.execute("DROP POLICY IF EXISTS products_read_authenticated ON products")
    op.execute("ALTER TABLE products NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE products DISABLE ROW LEVEL SECURITY")
    op.drop_index("uq_products_name_ci", table_name="products")
    op.drop_index("ix_lots_holder_product_harvested", table_name="lots")
