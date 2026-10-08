"""Add harvest lot fields after the historic revision-08 marker.

Revision ID: 20261008_15
Revises: 20261007_08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

revision: str = "20261008_15"
down_revision: str | None = "20261007_08"
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


def _policy_exists(name: str) -> bool:
    return bool(
        op.get_bind()
        .execute(
            sa.text(
                "SELECT EXISTS ("
                "SELECT 1 FROM pg_catalog.pg_policies "
                "WHERE schemaname = current_schema() "
                "AND tablename = 'lots' AND policyname = :name"
                ")"
            ),
            {"name": name},
        )
        .scalar()
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("lots")}

    missing_columns = (
        ("lot_code", sa.Column("lot_code", sa.String(length=12))),
        (
            "product_id",
            sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        ),
        ("harvested_on", sa.Column("harvested_on", sa.Date(), nullable=True)),
        (
            "quantity",
            sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=True),
        ),
    )
    for name, column in missing_columns:
        if name not in columns:
            op.add_column("lots", column)
            columns.add(name)

    foreign_keys = {item["name"] for item in inspector.get_foreign_keys("lots")}
    if "fk_lots_product_id_products" not in foreign_keys:
        op.create_foreign_key(
            "fk_lots_product_id_products",
            "lots",
            "products",
            ["product_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    checks = {item["name"] for item in inspector.get_check_constraints("lots")}
    if "ck_lots_quantity_positive" not in checks:
        op.create_check_constraint(
            "ck_lots_quantity_positive",
            "lots",
            "quantity IS NULL OR (quantity > 0 AND quantity < 'Infinity'::numeric)",
        )

    indexes = {item["name"] for item in inspector.get_indexes("lots")}
    if "ix_lots_product_id" not in indexes:
        op.create_index("ix_lots_product_id", "lots", ["product_id"])
    if "ix_lots_organization_harvested_on" not in indexes:
        op.create_index(
            "ix_lots_organization_harvested_on",
            "lots",
            ["organization_id", "harvested_on"],
        )
    if "uq_lots_lot_code" not in indexes:
        op.create_index("uq_lots_lot_code", "lots", ["lot_code"], unique=True)

    if not _policy_exists("lots_insert_tenant"):
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
