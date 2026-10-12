"""Scope provenance reads and historical event cutoffs in database policies."""

import sqlalchemy as sa

from alembic import op
from app.core.config import settings

revision = "20261011_18"
down_revision = "20261011_17"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE lot_relations NO FORCE ROW LEVEL SECURITY")
    # Fixed search_path, no caller-supplied org, and revoked PUBLIC execution are
    # essential: policy queries must bypass their own RLS without exposing data.
    op.execute("""CREATE FUNCTION public.app_readable_lot_ids() RETURNS SETOF uuid
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
    op.execute("""CREATE FUNCTION public.app_event_cutoff(target uuid) RETURNS timestamptz
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
      SELECT CASE WHEN public.app_current_role() IN ('inspector','system_admin')
        OR EXISTS (SELECT 1 FROM public.lots WHERE id = target AND current_holder_organization_id = public.app_current_organization_id())
        THEN NULL ELSE (SELECT max(resolved_at) FROM public.handovers WHERE lot_id = target
          AND status = 'accepted' AND from_organization_id = public.app_current_organization_id()) END;
    $$""")
    op.execute(
        "REVOKE ALL ON FUNCTION public.app_readable_lot_ids(), public.app_event_cutoff(uuid) FROM PUBLIC"
    )
    bind = op.get_bind()
    if bind.execute(
        sa.text(
            "SELECT 1 FROM pg_roles WHERE rolname = :role AND :role <> current_user"
        ),
        {"role": settings.DB_USER},
    ).scalar():
        role = bind.dialect.identifier_preparer.quote(settings.DB_USER)
        op.execute(
            f"GRANT EXECUTE ON FUNCTION public.app_readable_lot_ids(), public.app_event_cutoff(uuid) TO {role}"
        )
    op.execute("DROP POLICY lots_read_tenant_or_inspector ON lots")
    op.execute(
        "CREATE POLICY lots_read_tenant_or_inspector ON lots FOR SELECT USING (id IN (SELECT public.app_readable_lot_ids()))"
    )
    op.execute("DROP POLICY lot_relations_read ON lot_relations")
    op.execute("""CREATE POLICY lot_relations_read ON lot_relations FOR SELECT USING (
      parent_lot_id IN (SELECT public.app_readable_lot_ids())
      AND child_lot_id IN (SELECT public.app_readable_lot_ids()))""")
    op.execute("DROP POLICY events_read_tenant_or_inspector ON events")
    op.execute("""CREATE POLICY events_read_tenant_or_inspector ON events FOR SELECT USING (
      lot_id IN (SELECT public.app_readable_lot_ids())
      AND recorded_at <= COALESCE(public.app_event_cutoff(lot_id), 'infinity'::timestamptz))""")
    op.execute("""CREATE POLICY farms_lineage_read ON farms FOR SELECT USING (
      id IN (SELECT farm_id FROM lots WHERE id IN (SELECT public.app_readable_lot_ids())))""")
    op.execute("""CREATE POLICY organizations_lineage_read ON organizations FOR SELECT USING (
      id IN (SELECT organization_id FROM lots WHERE id IN (SELECT public.app_readable_lot_ids()))
      OR id IN (SELECT current_holder_organization_id FROM lots WHERE id IN (SELECT public.app_readable_lot_ids())))""")


def downgrade():
    op.execute("DROP POLICY organizations_lineage_read ON organizations")
    op.execute("DROP POLICY farms_lineage_read ON farms")
    op.execute("DROP POLICY lot_relations_read ON lot_relations")
    op.execute("""CREATE POLICY lot_relations_read ON lot_relations FOR SELECT USING (
      organization_id = public.app_current_organization_id() OR public.app_current_role() IN ('inspector','system_admin'))""")
    op.execute("DROP POLICY events_read_tenant_or_inspector ON events")
    op.execute("""CREATE POLICY events_read_tenant_or_inspector ON events FOR SELECT USING (
      organization_id = public.app_current_organization_id() OR public.app_current_role() IN ('inspector','system_admin')
      OR EXISTS (SELECT 1 FROM lots l WHERE l.id = events.lot_id AND (
        l.current_holder_organization_id = public.app_current_organization_id()
        OR EXISTS (SELECT 1 FROM handovers h WHERE h.lot_id = l.id AND h.status = 'pending' AND h.to_organization_id = public.app_current_organization_id()))))""")
    op.execute("DROP POLICY lots_read_tenant_or_inspector ON lots")
    op.execute("""CREATE POLICY lots_read_tenant_or_inspector ON lots FOR SELECT USING (
      current_holder_organization_id = public.app_current_organization_id() OR public.app_current_role() IN ('inspector','system_admin')
      OR EXISTS (SELECT 1 FROM handovers h WHERE h.lot_id = lots.id AND h.status = 'pending' AND h.to_organization_id = public.app_current_organization_id()))""")
    op.execute("DROP FUNCTION public.app_event_cutoff(uuid)")
    op.execute("DROP FUNCTION public.app_readable_lot_ids()")
