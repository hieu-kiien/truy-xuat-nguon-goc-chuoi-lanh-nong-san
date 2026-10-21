"""Add processing steps for cooperative lots (N3-27).

A cooperative records that a lot went through a processing step (washing,
packing) together with the parameters of that step. Every record becomes one
event on the lot chain, and the public page only shows a short summary of the
steps, never the parameters.

Revision ID: 20261021_38
Revises: 20261021_37
Create Date: 2026-10-21 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "20261021_38"
down_revision: str | Sequence[str] | None = "20261021_37"
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
    # 1. The catalogue of processing steps, shared by every organization.
    op.create_table(
        "processing_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=48), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "parameter_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(code)) > 0", name="ck_processing_steps_code_nonblank"
        ),
        sa.CheckConstraint(
            "length(btrim(name)) > 0", name="ck_processing_steps_name_nonblank"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_processing_steps_code"),
    )
    op.execute("ALTER TABLE processing_steps ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY processing_steps_read_authenticated ON processing_steps
        FOR SELECT
        USING (public.app_current_user_id() IS NOT NULL)
        """
    )
    op.execute(
        """
        CREATE POLICY processing_steps_write_admin ON processing_steps
        FOR INSERT
        WITH CHECK (public.app_current_role() = 'system_admin')
        """
    )
    op.execute(
        """
        CREATE POLICY processing_steps_update_admin ON processing_steps
        FOR UPDATE
        USING (public.app_current_role() = 'system_admin')
        WITH CHECK (public.app_current_role() = 'system_admin')
        """
    )

    # 2. The records of the steps a lot went through.
    op.create_table(
        "lot_processing_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_step_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["processing_step_id"], ["processing_steps.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lot_processing_steps_lot_occurred",
        "lot_processing_steps",
        ["lot_id", "occurred_at"],
    )
    op.create_index(
        "ix_lot_processing_steps_organization_created",
        "lot_processing_steps",
        ["organization_id", "created_at"],
    )
    op.execute("ALTER TABLE lot_processing_steps ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY lot_processing_steps_read_tenant_or_auditor
        ON lot_processing_steps
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
        )
        """
    )
    op.execute(
        """
        CREATE POLICY lot_processing_steps_insert_tenant
        ON lot_processing_steps
        FOR INSERT
        WITH CHECK (
            organization_id = public.app_current_organization_id()
        )
        """
    )

    # 3. The public page only shows the names of the steps, never the values.
    #    The return type changes, so the old function has to go first.
    op.execute("DROP FUNCTION IF EXISTS public.app_public_lot_trace(text)")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_public_lot_trace(p_lot_code text)
        RETURNS TABLE(
            lot_code text,
            status text,
            harvested_on date,
            product_name text,
            product_unit text,
            farm_name text,
            origin_organization_type text,
            recall_active boolean,
            cold_chain_violation boolean,
            processing_summary text
        )
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path TO 'pg_catalog', 'public'
        AS $function$
        WITH RECURSIVE target AS (
            SELECT l.id, l.lot_code, l.status, l.harvested_on, l.farm_id, l.product_id,
                   l.organization_id
            FROM public.lots l
            WHERE l.lot_code = upper(btrim(p_lot_code))
        ), ancestor_ids AS (
            SELECT t.id FROM target t
            UNION
            SELECT r.parent_lot_id
            FROM public.lot_relations r
            JOIN ancestor_ids a ON r.child_lot_id = a.id
        ), recall AS (
            SELECT EXISTS (
                SELECT 1
                FROM public.recall_order_lots rol
                JOIN public.recall_orders ro ON ro.id = rol.recall_order_id
                WHERE rol.lot_id IN (SELECT a.id FROM ancestor_ids a)
                  AND (ro.status = 'open' OR (ro.status = 'completed' AND rol.incident_flag))
            ) AS active
        ), violation AS (
            SELECT EXISTS (
                SELECT 1
                FROM public.events e
                WHERE e.lot_id IN (SELECT t.id FROM target t)
                  AND e.event_type = 'cold_chain_violation'
            ) AS had
        ), steps AS (
            SELECT string_agg(DISTINCT ps.name, ', ' ORDER BY ps.name) AS names
            FROM public.lot_processing_steps lps
            JOIN public.processing_steps ps ON ps.id = lps.processing_step_id
            WHERE lps.lot_id IN (SELECT a.id FROM ancestor_ids a)
        )
        SELECT t.lot_code, t.status, t.harvested_on, p.name, p.unit::text, f.name,
               o.organization_type, r.active, v.had, s.names
        FROM target t
        LEFT JOIN public.products p ON p.id = t.product_id
        LEFT JOIN public.farms f ON f.id = t.farm_id
        LEFT JOIN public.organizations o ON o.id = t.organization_id
        CROSS JOIN recall r
        CROSS JOIN violation v
        LEFT JOIN steps s ON true
        $function$;
        """
    )

    role = _application_role()
    if role:
        op.execute(f"GRANT SELECT ON processing_steps TO {role}")
        op.execute(f"GRANT INSERT, UPDATE ON processing_steps TO {role}")
        op.execute(f"REVOKE DELETE ON processing_steps FROM {role}")
        op.execute(f"GRANT SELECT, INSERT ON lot_processing_steps TO {role}")
        op.execute(f"REVOKE UPDATE, DELETE ON lot_processing_steps FROM {role}")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS public.app_public_lot_trace(text)")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_public_lot_trace(p_lot_code text)
        RETURNS TABLE(
            lot_code text,
            status text,
            harvested_on date,
            product_name text,
            product_unit text,
            farm_name text,
            origin_organization_type text,
            recall_active boolean,
            cold_chain_violation boolean
        )
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path TO 'pg_catalog', 'public'
        AS $function$
        WITH RECURSIVE target AS (
            SELECT l.id, l.lot_code, l.status, l.harvested_on, l.farm_id, l.product_id,
                   l.organization_id
            FROM public.lots l
            WHERE l.lot_code = upper(btrim(p_lot_code))
        ), ancestor_ids AS (
            SELECT t.id FROM target t
            UNION
            SELECT r.parent_lot_id
            FROM public.lot_relations r
            JOIN ancestor_ids a ON r.child_lot_id = a.id
        ), recall AS (
            SELECT EXISTS (
                SELECT 1
                FROM public.recall_order_lots rol
                JOIN public.recall_orders ro ON ro.id = rol.recall_order_id
                WHERE rol.lot_id IN (SELECT a.id FROM ancestor_ids a)
                  AND (ro.status = 'open' OR (ro.status = 'completed' AND rol.incident_flag))
            ) AS active
        ), violation AS (
            SELECT EXISTS (
                SELECT 1
                FROM public.events e
                WHERE e.lot_id IN (SELECT t.id FROM target t)
                  AND e.event_type = 'cold_chain_violation'
            ) AS had
        )
        SELECT t.lot_code, t.status, t.harvested_on, p.name, p.unit::text, f.name,
               o.organization_type, r.active, v.had
        FROM target t
        LEFT JOIN public.products p ON p.id = t.product_id
        LEFT JOIN public.farms f ON f.id = t.farm_id
        LEFT JOIN public.organizations o ON o.id = t.organization_id
        CROSS JOIN recall r
        CROSS JOIN violation v
        $function$;
        """
    )

    role = _application_role()
    if role:
        op.execute(f"REVOKE SELECT, INSERT ON lot_processing_steps FROM {role}")
        op.execute(f"REVOKE SELECT, INSERT, UPDATE ON processing_steps FROM {role}")

    op.execute(
        "DROP POLICY IF EXISTS lot_processing_steps_insert_tenant "
        "ON lot_processing_steps"
    )
    op.execute(
        "DROP POLICY IF EXISTS lot_processing_steps_read_tenant_or_auditor "
        "ON lot_processing_steps"
    )
    op.execute("ALTER TABLE lot_processing_steps DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_lot_processing_steps_organization_created",
        table_name="lot_processing_steps",
    )
    op.drop_index(
        "ix_lot_processing_steps_lot_occurred", table_name="lot_processing_steps"
    )
    op.drop_table("lot_processing_steps")

    op.execute(
        "DROP POLICY IF EXISTS processing_steps_update_admin ON processing_steps"
    )
    op.execute("DROP POLICY IF EXISTS processing_steps_write_admin ON processing_steps")
    op.execute(
        "DROP POLICY IF EXISTS processing_steps_read_authenticated ON processing_steps"
    )
    op.execute("ALTER TABLE processing_steps DISABLE ROW LEVEL SECURITY")
    op.drop_table("processing_steps")
