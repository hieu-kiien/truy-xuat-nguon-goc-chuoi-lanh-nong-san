"""Preserve ancestor history for former custodians with transfer-time cutoffs."""

from alembic import op

revision = "20261012_22"
down_revision = "20261011_21"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE OR REPLACE FUNCTION public.app_readable_lot_ids() RETURNS SETOF uuid
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
    $$""")
    op.execute("""CREATE OR REPLACE FUNCTION public.app_event_cutoff(target uuid) RETURNS timestamptz
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
  WITH RECURSIVE downstream(id) AS (
    SELECT target UNION
    SELECT r.child_lot_id FROM public.lot_relations r JOIN downstream d ON r.parent_lot_id = d.id
  ) SELECT CASE WHEN public.app_current_role() IN ('inspector','system_admin')
    OR EXISTS (SELECT 1 FROM public.lots l JOIN downstream d ON d.id=l.id
               WHERE l.current_holder_organization_id=public.app_current_organization_id())
    OR EXISTS (SELECT 1 FROM public.handovers h JOIN downstream d ON d.id=h.lot_id
               WHERE h.status='pending' AND h.to_organization_id=public.app_current_organization_id())
    THEN NULL ELSE (SELECT max(h.resolved_at) FROM public.handovers h
      JOIN downstream d ON d.id=h.lot_id WHERE h.status='accepted'
      AND h.from_organization_id=public.app_current_organization_id()) END;
$$""")


def downgrade():
    op.execute("""CREATE OR REPLACE FUNCTION public.app_readable_lot_ids() RETURNS SETOF uuid
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
      WITH RECURSIVE context AS MATERIALIZED (
        SELECT public.app_current_organization_id() AS org, public.app_current_role() AS role
      ), direct(id) AS (
        SELECT id FROM public.lots CROSS JOIN context WHERE
          current_holder_organization_id = context.org
          OR context.role IN ('inspector', 'system_admin')
        UNION SELECT lot_id FROM public.handovers CROSS JOIN context WHERE
          (status = 'pending' AND to_organization_id = context.org)
      ), sources(id) AS (
        SELECT id FROM direct
        UNION SELECT r.parent_lot_id FROM public.lot_relations r JOIN sources s ON r.child_lot_id = s.id
      ) SELECT id FROM sources
        UNION SELECT lot_id FROM public.handovers CROSS JOIN context WHERE
          status = 'accepted' AND from_organization_id = context.org;
    $$""")
    op.execute("""CREATE OR REPLACE FUNCTION public.app_event_cutoff(target uuid) RETURNS timestamptz
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
      SELECT CASE WHEN public.app_current_role() IN ('inspector','system_admin')
        OR EXISTS (SELECT 1 FROM public.lots WHERE id = target AND current_holder_organization_id = public.app_current_organization_id())
        THEN NULL ELSE (SELECT max(resolved_at) FROM public.handovers WHERE lot_id = target
          AND status = 'accepted' AND from_organization_id = public.app_current_organization_id()) END;
    $$""")
