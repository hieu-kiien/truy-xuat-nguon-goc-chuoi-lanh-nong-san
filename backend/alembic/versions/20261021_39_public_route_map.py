"""Add the public route map of a lot (N3-70).

The public page shows where a lot travelled: the growing area it came from
and the main stops along the way, in order. The coordinates are rounded to the
district level, so the exact plot never leaves the system, and the map library
is an open source one.

Revision ID: 20261021_39
Revises: 20261021_38
Create Date: 2026-10-21 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "20261021_39"
down_revision: str | Sequence[str] | None = "20261021_38"
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
    # The route of a lot: the growing area it came from and the main stops of
    # the journey, ordered from the origin to the lot. The coordinates are
    # rounded to two decimals, which is about the district level, so the exact
    # plot is never published.
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
    role = _application_role()
    if role:
        op.execute(
            f"GRANT EXECUTE ON FUNCTION public.app_public_lot_route(text) TO {role}"
        )


def downgrade() -> None:
    role = _application_role()
    if role:
        op.execute(
            f"REVOKE EXECUTE ON FUNCTION public.app_public_lot_route(text) FROM {role}"
        )
    op.execute("DROP FUNCTION IF EXISTS public.app_public_lot_route(text)")
