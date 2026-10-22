"""Fix public trace/route ancestor resolution and clear organization contact_email on PII erase.

Revision ID: 20261021_44
Revises: 20261021_43
Create Date: 2026-10-21 21:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "20261021_44"
down_revision: str | Sequence[str] | None = "20261021_43"
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
    if not exists:
        return None
    return bind.dialect.identifier_preparer.quote(settings.DB_USER)


def upgrade() -> None:
    # 1. Clear organizations.contact_email when anonymizing an organization.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_anonymize_organization(
            target_organization uuid, target_farm uuid
        )
        RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public AS $$
        BEGIN
          IF public.app_current_role() <> 'system_admin' THEN
            RAISE EXCEPTION 'Only a system administrator may erase identifying data';
          END IF;
          IF target_organization IS NULL OR target_farm IS NULL THEN
            RAISE EXCEPTION 'Missing organization or farm';
          END IF;
          UPDATE public.users u SET
            full_name = 'Nông hộ ẩn danh #' || upper(substr(replace(u.id::text, '-', ''), 1, 8)),
            email = 'anonymized+' || replace(u.id::text, '-', '') || '@anonymized.invalid'
          WHERE u.organization_id = target_organization;
          UPDATE public.organizations o SET
            name = 'Tổ chức ẩn danh #' || upper(substr(replace(o.id::text, '-', ''), 1, 8)),
            contact_email = NULL
          WHERE o.id = target_organization;
          UPDATE public.farms f SET
            name = 'Vùng trồng ẩn danh #' || upper(substr(replace(f.id::text, '-', ''), 1, 8)),
            latitude = NULL,
            longitude = NULL
          WHERE f.id = target_farm AND f.organization_id = target_organization;
        END; $$
        """
    )

    # 2. Public lot trace: fall back to ancestor farm/harvest date for split,
    #    merged or derived lots, propagate ancestor cold_chain_violation, and
    #    keep the processing_summary column from revision 20261021_38.
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
        ), ancestors AS (
            SELECT t.id, t.harvested_on, t.farm_id, t.organization_id, 0 AS depth
            FROM target t
            UNION ALL
            SELECT parent.id, parent.harvested_on, parent.farm_id, parent.organization_id,
                   a.depth + 1
            FROM public.lot_relations r
            JOIN ancestors a ON r.child_lot_id = a.id
            JOIN public.lots parent ON parent.id = r.parent_lot_id
            WHERE a.depth < 32
        ), origin_lot AS (
            SELECT a.farm_id, a.harvested_on, a.organization_id
            FROM ancestors a
            WHERE a.farm_id IS NOT NULL
            ORDER BY a.depth ASC
            LIMIT 1
        ), root_org AS (
            SELECT a.organization_id
            FROM ancestors a
            ORDER BY a.depth DESC
            LIMIT 1
        ), recall AS (
            SELECT EXISTS (
                SELECT 1
                FROM public.recall_order_lots rol
                JOIN public.recall_orders ro ON ro.id = rol.recall_order_id
                WHERE rol.lot_id IN (SELECT a.id FROM ancestors a)
                  AND (ro.status = 'open' OR (ro.status = 'completed' AND rol.incident_flag))
            ) AS active
        ), violation AS (
            SELECT EXISTS (
                SELECT 1
                FROM public.events e
                WHERE e.lot_id IN (SELECT a.id FROM ancestors a)
                  AND e.event_type = 'cold_chain_violation'
            ) AS had
        ), steps AS (
            SELECT string_agg(DISTINCT ps.name, ', ' ORDER BY ps.name) AS names
            FROM public.lot_processing_steps lps
            JOIN public.processing_steps ps ON ps.id = lps.processing_step_id
            WHERE lps.lot_id IN (SELECT a.id FROM ancestors a)
        )
        SELECT t.lot_code,
               t.status,
               COALESCE(t.harvested_on, ol.harvested_on),
               p.name,
               p.unit::text,
               f.name,
               o.organization_type,
               r.active,
               v.had,
               s.names
        FROM target t
        LEFT JOIN origin_lot ol ON true
        LEFT JOIN root_org ro_org ON true
        LEFT JOIN public.products p ON p.id = t.product_id
        LEFT JOIN public.farms f ON f.id = COALESCE(t.farm_id, ol.farm_id)
        LEFT JOIN public.organizations o
          ON o.id = COALESCE(ol.organization_id, ro_org.organization_id, t.organization_id)
        CROSS JOIN recall r
        CROSS JOIN violation v
        LEFT JOIN steps s ON true
        $function$;
        """
    )

    # 3. Public route map: mark the earliest ancestor farm as 'origin' even when
    #    the queried lot is a split/merged/derived child lot (depth > 0).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_public_lot_route(p_lot_code text)
        RETURNS TABLE(
            point_order integer,
            point_name text,
            point_kind text,
            point_latitude numeric,
            point_longitude numeric
        )
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path TO 'pg_catalog', 'public'
        AS $function$
        WITH RECURSIVE chain AS (
            SELECT l.id, l.farm_id, l.lot_code, l.product_id, 0 AS depth
            FROM public.lots l
            WHERE l.lot_code = upper(btrim(p_lot_code))
            UNION ALL
            SELECT parent.id, parent.farm_id, parent.lot_code, parent.product_id,
                   c.depth + 1
            FROM public.lot_relations r
            JOIN chain c ON r.child_lot_id = c.id
            JOIN public.lots parent ON parent.id = r.parent_lot_id
            WHERE c.depth < 32
        ), dedup_farms AS (
            SELECT f.id,
                   f.name,
                   f.latitude,
                   f.longitude,
                   MAX(c.depth) AS depth
            FROM chain c
            JOIN public.farms f ON f.id = c.farm_id
            GROUP BY f.id, f.name, f.latitude, f.longitude
        ), farm_points AS (
            SELECT (1000 - df.depth)::integer AS point_order,
                   df.name AS point_name,
                   CASE
                       WHEN row_number() OVER (ORDER BY df.depth DESC, df.name ASC) = 1 THEN 'origin'
                       ELSE 'stop'
                   END AS point_kind,
                   round(df.latitude, 2) AS point_latitude,
                   round(df.longitude, 2) AS point_longitude,
                   df.depth
            FROM dedup_farms df
        )
        SELECT fp.point_order,
               fp.point_name,
               fp.point_kind,
               fp.point_latitude,
               fp.point_longitude
        FROM farm_points fp
        ORDER BY fp.depth DESC, fp.point_name ASC
        $function$;
        """
    )

    op.execute(
        "REVOKE ALL ON FUNCTION public.app_anonymize_organization(uuid, uuid) FROM PUBLIC"
    )
    op.execute("REVOKE ALL ON FUNCTION public.app_public_lot_trace(text) FROM PUBLIC")
    op.execute("REVOKE ALL ON FUNCTION public.app_public_lot_route(text) FROM PUBLIC")

    # 4. Optimize lineage organization and farm RLS policies so large graphs
    #    (1,000+ nodes) evaluate app_readable_lot_ids() once per statement
    #    rather than nested-looping over lots RLS per organization/farm row.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_readable_organization_ids()
        RETURNS SETOF uuid
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
            WITH readable AS MATERIALIZED (
                SELECT public.app_readable_lot_ids() AS id
            )
            SELECT l.organization_id
            FROM public.lots AS l
            JOIN readable AS r ON r.id = l.id
            UNION
            SELECT l.current_holder_organization_id
            FROM public.lots AS l
            JOIN readable AS r ON r.id = l.id;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_readable_farm_ids()
        RETURNS SETOF uuid
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
            WITH readable AS MATERIALIZED (
                SELECT public.app_readable_lot_ids() AS id
            )
            SELECT l.farm_id
            FROM public.lots AS l
            JOIN readable AS r ON r.id = l.id
            WHERE l.farm_id IS NOT NULL;
        $$;
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION public.app_readable_organization_ids(), public.app_readable_farm_ids() FROM PUBLIC"
    )
    op.execute("DROP POLICY IF EXISTS organizations_lineage_read ON organizations")
    op.execute(
        """
        CREATE POLICY organizations_lineage_read ON organizations
        FOR SELECT
        USING (id IN (SELECT public.app_readable_organization_ids()))
        """
    )
    op.execute("DROP POLICY IF EXISTS farms_lineage_read ON farms")
    op.execute(
        """
        CREATE POLICY farms_lineage_read ON farms
        FOR SELECT
        USING (id IN (SELECT public.app_readable_farm_ids()))
        """
    )

    role = _application_role()
    if role:
        op.execute(
            f"GRANT EXECUTE ON FUNCTION public.app_anonymize_organization(uuid, uuid) TO {role}"
        )
        op.execute(
            f"GRANT EXECUTE ON FUNCTION public.app_public_lot_trace(text) TO {role}"
        )
        op.execute(
            f"GRANT EXECUTE ON FUNCTION public.app_public_lot_route(text) TO {role}"
        )
        op.execute(
            f"GRANT EXECUTE ON FUNCTION public.app_readable_organization_ids(), public.app_readable_farm_ids() TO {role}"
        )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS organizations_lineage_read ON organizations")
    op.execute(
        """
        CREATE POLICY organizations_lineage_read ON organizations FOR SELECT USING (
            id IN (SELECT organization_id FROM lots WHERE id IN (SELECT public.app_readable_lot_ids()))
            OR id IN (SELECT current_holder_organization_id FROM lots WHERE id IN (SELECT public.app_readable_lot_ids()))
        )
        """
    )
    op.execute("DROP POLICY IF EXISTS farms_lineage_read ON farms")
    op.execute(
        """
        CREATE POLICY farms_lineage_read ON farms FOR SELECT USING (
            id IN (SELECT farm_id FROM lots WHERE id IN (SELECT public.app_readable_lot_ids()))
        )
        """
    )
    op.execute("DROP FUNCTION IF EXISTS public.app_readable_farm_ids()")
    op.execute("DROP FUNCTION IF EXISTS public.app_readable_organization_ids()")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_anonymize_organization(
            target_organization uuid, target_farm uuid
        )
        RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public AS $$
        BEGIN
          IF public.app_current_role() <> 'system_admin' THEN
            RAISE EXCEPTION 'Only a system administrator may erase identifying data';
          END IF;
          IF target_organization IS NULL OR target_farm IS NULL THEN
            RAISE EXCEPTION 'Missing organization or farm';
          END IF;
          UPDATE public.users u SET
            full_name = 'Nông hộ ẩn danh #' || upper(substr(replace(u.id::text, '-', ''), 1, 8)),
            email = 'anonymized+' || replace(u.id::text, '-', '') || '@anonymized.invalid'
          WHERE u.organization_id = target_organization;
          UPDATE public.organizations o SET
            name = 'Tổ chức ẩn danh #' || upper(substr(replace(o.id::text, '-', ''), 1, 8))
          WHERE o.id = target_organization;
          UPDATE public.farms f SET
            name = 'Vùng trồng ẩn danh #' || upper(substr(replace(f.id::text, '-', ''), 1, 8)),
            latitude = NULL,
            longitude = NULL
          WHERE f.id = target_farm AND f.organization_id = target_organization;
        END; $$
        """
    )

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

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_public_lot_route(p_lot_code text)
        RETURNS TABLE(
            point_order integer,
            point_name text,
            point_kind text,
            point_latitude numeric,
            point_longitude numeric
        )
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path TO 'pg_catalog', 'public'
        AS $function$
        WITH RECURSIVE chain AS (
            SELECT l.id, l.farm_id, l.lot_code, l.product_id, 0 AS depth
            FROM public.lots l
            WHERE l.lot_code = upper(btrim(p_lot_code))
            UNION ALL
            SELECT parent.id, parent.farm_id, parent.lot_code, parent.product_id,
                   c.depth + 1
            FROM public.lot_relations r
            JOIN chain c ON r.child_lot_id = c.id
            JOIN public.lots parent ON parent.id = r.parent_lot_id
        )
        SELECT (1000 - c.depth)::integer,
               f.name,
               CASE WHEN c.depth = 0 THEN 'origin' ELSE 'stop' END,
               round(f.latitude, 2),
               round(f.longitude, 2)
        FROM chain c
        JOIN public.farms f ON f.id = c.farm_id
        ORDER BY c.depth DESC
        $function$;
        """
    )
