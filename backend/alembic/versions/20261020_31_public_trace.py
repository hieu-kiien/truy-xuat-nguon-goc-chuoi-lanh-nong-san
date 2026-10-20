"""Public traceability read path with an explicit public projection (S-48).

Trang công khai không có phiên đăng nhập nên mọi truy vấn qua vai trò ứng dụng
bị PostgreSQL RLS chặn. Hàm SECURITY DEFINER này trả về đúng tập trường an toàn
cho khách xem công khai; danh sách trường giữ ở một nơi trong Python
(app/core/public_fields.py) và được test đối chiếu với phản hồi.
"""

import sqlalchemy as sa

from alembic import op
from app.core.config import settings

revision: str = "20261020_31"
down_revision: str | None = "20261020_30"
branch_labels = None
depends_on = None


PUBLIC_LOT_TRACE_FUNCTION = """
CREATE FUNCTION public.app_public_lot_trace(p_lot_code text)
RETURNS TABLE (
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
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
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
$$
"""


def upgrade():
    # Fixed search_path and revoked PUBLIC execution keep the function from
    # being used as a privilege-escalation or search_path-hijack surface.
    op.execute(PUBLIC_LOT_TRACE_FUNCTION)
    op.execute("REVOKE ALL ON FUNCTION public.app_public_lot_trace(text) FROM PUBLIC")
    bind = op.get_bind()
    if bind.execute(
        sa.text(
            "SELECT 1 FROM pg_roles WHERE rolname = :role AND :role <> current_user"
        ),
        {"role": settings.DB_USER},
    ).scalar():
        role = bind.dialect.identifier_preparer.quote(settings.DB_USER)
        op.execute(
            f"GRANT EXECUTE ON FUNCTION public.app_public_lot_trace(text) TO {role}"
        )


def downgrade():
    op.execute("DROP FUNCTION public.app_public_lot_trace(text)")
