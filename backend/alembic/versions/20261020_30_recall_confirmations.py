"""Add recall_confirmations table, immutability trigger, and recall lineage visibility (N3-50, N3-52, N3-55).

Revision ID: 20261020_30
Revises: 20261019_29
Create Date: 2026-10-20 17:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "20261020_30"
down_revision: str | Sequence[str] | None = "20261019_29"
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
    # 1. Create recall_confirmations table (append-only)
    op.create_table(
        "recall_confirmations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("recall_order_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("confirmed_by_user_id", sa.UUID(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column(
            "confirmed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(note)) > 0",
            name="ck_recall_confirmations_note_nonblank",
        ),
        sa.ForeignKeyConstraint(
            ["recall_order_id"],
            ["recall_orders.id"],
            name="fk_recall_confirmations_recall_order_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_recall_confirmations_org_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by_user_id"],
            ["users.id"],
            name="fk_recall_confirmations_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "recall_order_id",
            "organization_id",
            name="uq_recall_confirmations_order_org",
        ),
    )
    op.create_index(
        "ix_recall_confirmations_recall_order_id",
        "recall_confirmations",
        ["recall_order_id"],
        unique=False,
    )
    op.create_index(
        "ix_recall_confirmations_organization_id",
        "recall_confirmations",
        ["organization_id"],
        unique=False,
    )

    # 2. Immutability trigger on recall_confirmations (N3-55 non-functional: append-only)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_recall_confirmations_append_only()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Xác nhận xử lý thu hồi là sự kiện bất biến (append-only), không được phép sửa hoặc xóa.';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_recall_confirmations_immutable
        BEFORE UPDATE OR DELETE ON recall_confirmations
        FOR EACH ROW EXECUTE FUNCTION trg_recall_confirmations_append_only();
        """
    )

    # 3. Helper function to return all lot IDs in visible recall orders (N3-50)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_recall_affected_lot_ids()
        RETURNS SETOF uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
            WITH RECURSIVE all_recall_trees(recall_order_id, root_lot_id, opened_by_org_id, lot_id) AS (
                SELECT ro.id, ro.root_lot_id, ro.opened_by_organization_id, ro.root_lot_id
                FROM public.recall_orders ro
                UNION
                SELECT t.recall_order_id, t.root_lot_id, t.opened_by_org_id, r.child_lot_id
                FROM public.lot_relations r
                JOIN all_recall_trees t ON r.parent_lot_id = t.lot_id
            ),
            visible_orders(recall_order_id) AS (
                SELECT DISTINCT t.recall_order_id
                FROM all_recall_trees t
                LEFT JOIN public.lots l ON l.id = t.lot_id
                WHERE public.app_current_role() IN ('inspector', 'system_admin')
                   OR t.opened_by_org_id = public.app_current_organization_id()
                   OR l.current_holder_organization_id = public.app_current_organization_id()
                   OR l.organization_id = public.app_current_organization_id()
                   OR EXISTS (
                       SELECT 1 FROM public.recall_order_lots rol
                       WHERE rol.recall_order_id = t.recall_order_id
                         AND rol.organization_id = public.app_current_organization_id()
                   )
            )
            SELECT DISTINCT t.lot_id
            FROM all_recall_trees t
            JOIN visible_orders vo ON vo.recall_order_id = t.recall_order_id;
        $$
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION public.app_recall_affected_lot_ids() FROM PUBLIC"
    )

    # Expand app_readable_lot_ids() so lots in a recall order touching the caller's organization are readable
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_readable_lot_ids() RETURNS SETOF uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
          WITH RECURSIVE context AS MATERIALIZED (
            SELECT public.app_current_organization_id() AS org, public.app_current_role() AS role
          ), direct(id) AS (
            SELECT id FROM public.lots CROSS JOIN context WHERE
              current_holder_organization_id = context.org
              OR context.role IN ('inspector', 'system_admin')
            UNION SELECT lot_id FROM public.handovers CROSS JOIN context WHERE
              (status = 'pending' AND to_organization_id = context.org)
              OR (status = 'accepted' AND from_organization_id = context.org)
          ), sources(id) AS (
            SELECT id FROM direct
            UNION SELECT r.parent_lot_id FROM public.lot_relations r JOIN sources s ON r.child_lot_id = s.id
          ) SELECT id FROM sources
            UNION SELECT lot_id FROM public.handovers CROSS JOIN context WHERE
              status = 'accepted' AND from_organization_id = context.org
            UNION SELECT public.app_recall_affected_lot_ids();
        $$
        """
    )

    # 4. Enable RLS and policies on recall_confirmations
    op.execute("ALTER TABLE recall_confirmations ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY recall_confirmations_read ON recall_confirmations
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
            OR EXISTS (
                SELECT 1 FROM public.recall_orders AS ro
                WHERE ro.id = recall_confirmations.recall_order_id
                  AND (
                      ro.opened_by_organization_id = public.app_current_organization_id()
                      OR ro.root_lot_id IN (SELECT public.app_readable_lot_ids())
                  )
            )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY recall_confirmations_insert ON recall_confirmations
        FOR INSERT
        WITH CHECK (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
        )
        """
    )

    # 5. Update recall_orders policies so any involved organization can read and auto-complete recall orders
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

    op.execute("DROP POLICY IF EXISTS recall_orders_update ON recall_orders")
    op.execute(
        """
        CREATE POLICY recall_orders_update ON recall_orders
        FOR UPDATE
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
        WITH CHECK (
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

    # 6. Update events_insert_tenant so involved organizations can record recall_confirmed and recall_completed
    op.execute("DROP POLICY IF EXISTS events_insert_tenant ON events")
    op.execute(
        """
        CREATE POLICY events_insert_tenant ON events
        FOR INSERT
        WITH CHECK (
            organization_id = public.app_current_organization_id()
            AND (
                EXISTS (
                    SELECT 1 FROM public.lots AS l
                    WHERE l.id = events.lot_id
                      AND l.current_holder_organization_id = public.app_current_organization_id()
                )
                OR (
                    event_type IN ('handover_accepted', 'handover_rejected')
                    AND EXISTS (
                        SELECT 1 FROM public.handovers AS h
                        WHERE h.lot_id = events.lot_id
                          AND h.to_organization_id = public.app_current_organization_id()
                          AND h.status = 'pending'
                    )
                )
                OR (
                    event_type IN ('recall_opened', 'recall_confirmed', 'recall_completed')
                    AND (
                        public.app_current_role() IN ('inspector', 'system_admin')
                        OR events.lot_id IN (SELECT public.app_readable_lot_ids())
                    )
                )
            )
        )
        """
    )

    role = _application_role()
    if role:
        op.execute(f"GRANT SELECT, INSERT ON recall_confirmations TO {role}")
        op.execute(f"REVOKE UPDATE, DELETE ON recall_confirmations FROM {role}")
        op.execute(
            f"GRANT EXECUTE ON FUNCTION public.app_recall_affected_lot_ids() TO {role}"
        )


def downgrade() -> None:
    role = _application_role()
    if role:
        op.execute(f"REVOKE ALL ON recall_confirmations FROM {role}")
        op.execute(
            f"REVOKE ALL ON FUNCTION public.app_recall_affected_lot_ids() FROM {role}"
        )

    op.execute("DROP POLICY IF EXISTS events_insert_tenant ON events")
    op.execute(
        """
        CREATE POLICY events_insert_tenant ON events
        FOR INSERT
        WITH CHECK (
            organization_id = public.app_current_organization_id()
            AND (
                EXISTS (
                    SELECT 1 FROM public.lots AS l
                    WHERE l.id = events.lot_id
                      AND l.current_holder_organization_id = public.app_current_organization_id()
                )
                OR (
                    event_type IN ('handover_accepted', 'handover_rejected')
                    AND EXISTS (
                        SELECT 1 FROM public.handovers AS h
                        WHERE h.lot_id = events.lot_id
                          AND h.to_organization_id = public.app_current_organization_id()
                          AND h.status = 'pending'
                    )
                )
                OR (
                    event_type IN ('recall_opened', 'recall_completed')
                    AND public.app_current_role() IN ('inspector', 'system_admin')
                )
            )
        )
        """
    )

    op.execute("DROP POLICY IF EXISTS recall_orders_update ON recall_orders")
    op.execute(
        """
        CREATE POLICY recall_orders_update ON recall_orders
        FOR UPDATE
        USING (
            opened_by_organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
        )
        WITH CHECK (
            opened_by_organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
        )
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_readable_lot_ids() RETURNS SETOF uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
          WITH RECURSIVE context AS MATERIALIZED (
            SELECT public.app_current_organization_id() AS org, public.app_current_role() AS role
          ), direct(id) AS (
            SELECT id FROM public.lots CROSS JOIN context WHERE
              current_holder_organization_id = context.org
              OR context.role IN ('inspector', 'system_admin')
            UNION SELECT lot_id FROM public.handovers CROSS JOIN context WHERE
              (status = 'pending' AND to_organization_id = context.org)
              OR (status = 'accepted' AND from_organization_id = context.org)
          ), sources(id) AS (
            SELECT id FROM direct
            UNION SELECT r.parent_lot_id FROM public.lot_relations r JOIN sources s ON r.child_lot_id = s.id
          ) SELECT id FROM sources
            UNION SELECT lot_id FROM public.handovers CROSS JOIN context WHERE
              status = 'accepted' AND from_organization_id = context.org;
        $$
        """
    )

    op.execute("DROP TRIGGER IF EXISTS trg_recall_confirmations_immutable ON recall_confirmations")
    op.execute("DROP FUNCTION IF EXISTS trg_recall_confirmations_append_only()")
    op.execute("DROP POLICY IF EXISTS recall_confirmations_insert ON recall_confirmations")
    op.execute("DROP POLICY IF EXISTS recall_confirmations_read ON recall_confirmations")
    op.drop_table("recall_confirmations")
    op.execute("DROP FUNCTION IF EXISTS public.app_recall_affected_lot_ids()")
