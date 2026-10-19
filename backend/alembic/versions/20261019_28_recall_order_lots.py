"""Add recall_order_lots table and RLS policies for recall blocking (N3-53, S-38).

Revision ID: 20261019_28
Revises: 20261018_27
Create Date: 2026-10-19 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "20261019_28"
down_revision: str | Sequence[str] | None = "20261018_27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _application_role() -> str | None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text(
            "SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :role AND :role <> current_user"
        ),
        {"role": settings.DB_USER},
    ).scalar()
    return bind.dialect.identifier_preparer.quote(settings.DB_USER) if exists else None


def upgrade() -> None:
    op.create_table(
        "recall_order_lots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("recall_order_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("lot_id", sa.UUID(), nullable=False),
        sa.Column(
            "incident_flag",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["recall_order_id"],
            ["recall_orders.id"],
            name="fk_recall_order_lots_recall_order_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_recall_order_lots_org_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lot_id"],
            ["lots.id"],
            name="fk_recall_order_lots_lot_id_lots",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "recall_order_id", "lot_id", name="uq_recall_order_lots_order_lot"
        ),
    )
    op.create_index(
        "ix_recall_order_lots_recall_order_id",
        "recall_order_lots",
        ["recall_order_id"],
        unique=False,
    )
    op.create_index(
        "ix_recall_order_lots_lot_id",
        "recall_order_lots",
        ["lot_id"],
        unique=False,
    )

    op.execute("ALTER TABLE recall_order_lots ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY recall_order_lots_read ON recall_order_lots
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
            OR lot_id IN (SELECT public.app_readable_lot_ids())
        )
        """
    )
    op.execute(
        """
        CREATE POLICY recall_order_lots_insert ON recall_order_lots
        FOR INSERT
        WITH CHECK (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
        )
        """
    )
    op.execute(
        """
        CREATE POLICY recall_order_lots_update ON recall_order_lots
        FOR UPDATE
        USING (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
        )
        WITH CHECK (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
        )
        """
    )

    # Expand recall_orders_read so any participant holding a descendant lot in the
    # lineage graph (or listed in recall_order_lots) can read the recall order.
    op.execute("DROP POLICY IF EXISTS recall_orders_read ON recall_orders")
    op.execute(
        """
        CREATE POLICY recall_orders_read ON recall_orders
        FOR SELECT
        USING (
            opened_by_organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
            OR root_lot_id IN (SELECT public.app_readable_lot_ids())
            OR EXISTS (
                SELECT 1 FROM public.recall_order_lots AS rol
                WHERE rol.recall_order_id = recall_orders.id
                  AND rol.organization_id = public.app_current_organization_id()
            )
        )
        """
    )

    role = _application_role()
    if role:
        op.execute(f"GRANT SELECT, INSERT, DELETE ON recall_order_lots TO {role}")
        op.execute(f"GRANT UPDATE (incident_flag) ON recall_order_lots TO {role}")


def downgrade() -> None:
    role = _application_role()
    if role:
        op.execute(f"REVOKE ALL ON recall_order_lots FROM {role}")

    op.execute("DROP POLICY IF EXISTS recall_orders_read ON recall_orders")
    op.execute(
        """
        CREATE POLICY recall_orders_read ON recall_orders
        FOR SELECT
        USING (
            opened_by_organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
            OR EXISTS (
                SELECT 1 FROM public.lots AS l
                WHERE l.id = recall_orders.root_lot_id
                  AND l.current_holder_organization_id = public.app_current_organization_id()
            )
        )
        """
    )
    op.drop_table("recall_order_lots")
