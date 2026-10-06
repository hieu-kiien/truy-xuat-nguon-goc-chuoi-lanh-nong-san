"""Add generated lot codes and harvest details to lots.

Revision ID: 20261006_07
Revises: 20261006_06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

revision: str = "20261006_07"
down_revision: str | None = "20261006_06"
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
    op.add_column("lots", sa.Column("lot_code", sa.String(length=12)))
    op.add_column(
        "lots",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("lots", sa.Column("harvested_on", sa.Date(), nullable=True))
    op.add_column(
        "lots",
        sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=True),
    )
    op.create_foreign_key(
        "fk_lots_product_id_products",
        "lots",
        "products",
        ["product_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_lots_quantity_positive",
        "lots",
        "quantity IS NULL OR (quantity > 0 AND quantity < 'Infinity'::numeric)",
    )
    op.create_index("ix_lots_product_id", "lots", ["product_id"])
    op.create_index(
        "ix_lots_organization_harvested_on",
        "lots",
        ["organization_id", "harvested_on"],
    )
    op.create_index("uq_lots_lot_code", "lots", ["lot_code"], unique=True)

    op.execute(
        """
        CREATE POLICY lots_insert_tenant ON lots
        FOR INSERT
        WITH CHECK (
            organization_id = public.app_current_organization_id()
        )
        """
    )

    role = _application_role()
    if role:
        op.execute(f"GRANT SELECT, INSERT ON lots TO {role}")
        op.execute(f"REVOKE UPDATE, DELETE ON lots FROM {role}")


def downgrade() -> None:
    role = _application_role()
    if role:
        op.execute(f"REVOKE INSERT ON lots FROM {role}")

    op.execute("DROP POLICY IF EXISTS lots_insert_tenant ON lots")
    op.drop_index("uq_lots_lot_code", table_name="lots")
    op.drop_index("ix_lots_organization_harvested_on", table_name="lots")
    op.drop_index("ix_lots_product_id", table_name="lots")
    op.drop_constraint("ck_lots_quantity_positive", "lots", type_="check")
    op.drop_constraint("fk_lots_product_id_products", "lots", type_="foreignkey")
    op.drop_column("lots", "quantity")
    op.drop_column("lots", "harvested_on")
    op.drop_column("lots", "product_id")
    op.drop_column("lots", "lot_code")
