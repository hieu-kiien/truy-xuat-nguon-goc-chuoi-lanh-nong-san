"""Add SECURITY DEFINER helper to lock lot and read true event chain head on append.

Revision ID: 20261025_45
Revises: 20261021_44
Create Date: 2026-10-25 00:52:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "20261025_45"
down_revision: str | Sequence[str] | None = "20261021_44"
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
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_lock_and_get_lot_chain_head(target_lot_id uuid)
        RETURNS TABLE(sequence_number integer, event_hash character varying)
        LANGUAGE plpgsql
        VOLATILE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
        BEGIN
            PERFORM 1
            FROM public.lots AS l
            WHERE l.id = target_lot_id
            FOR UPDATE;

            RETURN QUERY
            SELECT e.sequence_number, e.event_hash
            FROM public.events AS e
            WHERE e.lot_id = target_lot_id
            ORDER BY e.sequence_number DESC
            LIMIT 1;
        END;
        $$;
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION public.app_lock_and_get_lot_chain_head(uuid) FROM PUBLIC"
    )
    role = _application_role()
    if role:
        op.execute(
            f"GRANT EXECUTE ON FUNCTION public.app_lock_and_get_lot_chain_head(uuid) TO {role}"
        )


def downgrade() -> None:
    role = _application_role()
    if role:
        op.execute(
            f"REVOKE ALL ON FUNCTION public.app_lock_and_get_lot_chain_head(uuid) FROM {role}"
        )
    op.execute("DROP FUNCTION IF EXISTS public.app_lock_and_get_lot_chain_head(uuid)")
