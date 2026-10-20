"""Add declarations of input materials for a harvested lot (N3-38).

A grower records which fertiliser or plant protection product was used for
a lot, with the date and the amount. Every declaration becomes one event on
the lot chain, so the record cannot be edited away later. Inspectors see the
declarations in the file, consumers do not.

Revision ID: 20261021_37
Revises: 20261021_36
Create Date: 2026-10-21 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "20261021_37"
down_revision: str | Sequence[str] | None = "20261021_36"
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
        "lot_input_lots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "quantity",
            sa.Numeric(precision=18, scale=3),
            nullable=False,
        ),
        sa.Column("used_on", sa.Date(), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("quantity > 0", name="ck_lot_input_lots_quantity_positive"),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lot_input_lots_lot_used_on",
        "lot_input_lots",
        ["lot_id", "used_on"],
    )
    op.create_index(
        "ix_lot_input_lots_organization_created",
        "lot_input_lots",
        ["organization_id", "created_at"],
    )

    op.execute("ALTER TABLE lot_input_lots ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY lot_input_lots_read_tenant_or_auditor ON lot_input_lots
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
        )
        """
    )
    op.execute(
        """
        CREATE POLICY lot_input_lots_insert_tenant ON lot_input_lots
        FOR INSERT
        WITH CHECK (
            organization_id = public.app_current_organization_id()
        )
        """
    )

    role = _application_role()
    if role:
        op.execute(f"GRANT SELECT, INSERT ON lot_input_lots TO {role}")
        op.execute(f"REVOKE UPDATE, DELETE ON lot_input_lots FROM {role}")


def downgrade() -> None:
    role = _application_role()
    if role:
        op.execute(f"REVOKE SELECT, INSERT ON lot_input_lots FROM {role}")

    op.execute("DROP POLICY IF EXISTS lot_input_lots_insert_tenant ON lot_input_lots")
    op.execute(
        "DROP POLICY IF EXISTS lot_input_lots_read_tenant_or_auditor ON lot_input_lots"
    )
    op.execute("ALTER TABLE lot_input_lots DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_lot_input_lots_organization_created", table_name="lot_input_lots")
    op.drop_index("ix_lot_input_lots_lot_used_on", table_name="lot_input_lots")
    op.drop_table("lot_input_lots")
