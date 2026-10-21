"""Restore the RLS branches lost when later revisions replaced whole policies.

Revision ID: 20261021_42
Revises: 20261021_41
Create Date: 2026-10-21 14:05:00.000000

Four policies were replaced instead of extended, so the branch that had been
added earlier disappeared:

1. ``events_insert_tenant`` lost the ``shipment_loaded`` and
   ``shipment_unloaded`` branch, so opening or closing a shipment raised an RLS
   error for a carrier that did not hold the lot.
2. ``cold_chain_violations_tenant_insert`` only accepted the owning carrier or
   the system admin, so an inspector reading a shipment raised an error.
3. ``shipments_read`` and the reading policy of
   ``temperature_hourly_aggregates`` lack the branch for a caller that still
   holds one of the lots of the shipment, which the application code already
   implements.

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "20261021_42"
down_revision: str | Sequence[str] | None = "20261021_41"
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
    # 0. A helper that answers "does this shipment still carry a lot of the
    #    caller?" without touching the RLS of shipments and shipment_lots.
    #    A plain subquery would be an infinite recursion, because the policy of
    #    shipment_lots reads shipments and the policy of shipments would read
    #    shipment_lots. The same pattern as app_readable_lot_ids.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_shipment_carries_lot_of(target uuid)
        RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = pg_catalog, public AS $$
            SELECT EXISTS (
                SELECT 1 FROM public.shipment_lots AS sl
                JOIN public.lots AS l ON l.id = sl.lot_id
                WHERE sl.shipment_id = target
                  AND sl.unloaded_at IS NULL
                  AND l.current_holder_organization_id = public.app_current_organization_id()
            );
        $$;
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION public.app_shipment_carries_lot_of(uuid) FROM PUBLIC"
    )

    # 1. Events: a shipment event belongs to the carrier that opens or closes
    #    the trip, not only to the holder of the lot.
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
                OR (
                    event_type IN ('shipment_loaded', 'shipment_unloaded')
                )
            )
        )
        """
    )

    # 2. Violations: an inspector reads a shipment of another organization and
    #    the detector records the violation it finds.
    op.execute(
        "DROP POLICY IF EXISTS cold_chain_violations_tenant_insert ON cold_chain_violations"
    )
    op.execute(
        """
        CREATE POLICY cold_chain_violations_tenant_insert ON cold_chain_violations
        FOR INSERT
        WITH CHECK (
            public.app_current_role() IN ('inspector', 'system_admin')
            OR EXISTS (
                SELECT 1 FROM public.shipments AS s
                WHERE s.id = cold_chain_violations.shipment_id
                  AND s.organization_id = public.app_current_organization_id()
            )
        )
        """
    )

    # 3. Shipments: a caller that still holds one of the lots of the shipment
    #    may see it, the same rule the raw readings already follow.
    op.execute("DROP POLICY IF EXISTS shipments_read ON shipments")
    op.execute(
        """
        CREATE POLICY shipments_read ON shipments
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
            OR public.app_shipment_carries_lot_of(shipments.id)
        )
        """
    )

    # 4. The same rule for the hourly aggregates, so the compacted series
    #    matches the raw readings.
    op.execute(
        "DROP POLICY IF EXISTS temperature_hourly_aggregates_read_tenant_or_auditor "
        "ON temperature_hourly_aggregates"
    )
    op.execute(
        """
        CREATE POLICY temperature_hourly_aggregates_read_tenant_or_auditor
        ON temperature_hourly_aggregates
        FOR SELECT
        USING (
            EXISTS (
                SELECT 1 FROM public.shipments AS s
                WHERE s.id = temperature_hourly_aggregates.shipment_id
                  AND (
                    s.organization_id = public.app_current_organization_id()
                    OR public.app_current_role() IN ('inspector', 'system_admin')
                    OR public.app_shipment_carries_lot_of(s.id)
                  )
            )
        )
        """
    )

    # 5. Repeat the privileges of the migrations. When the application role
    #    did not exist while the migrations ran, no GRANT was applied at all.
    role = _application_role()
    if role:
        op.execute(
            f"GRANT EXECUTE ON FUNCTION public.app_shipment_carries_lot_of(uuid) TO {role}"
        )
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE ON organization_invitations TO {role}"
        )
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON email_outbox TO {role}")
        op.execute(f"GRANT SELECT, INSERT ON lot_input_lots TO {role}")
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON processing_steps TO {role}")
        op.execute(f"GRANT SELECT, INSERT ON lot_processing_steps TO {role}")
        op.execute(f"GRANT SELECT, INSERT ON integrity_checks TO {role}")
        op.execute(f"GRANT SELECT, INSERT ON temperature_hourly_aggregates TO {role}")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS public.app_shipment_carries_lot_of(uuid)")

    # The policies are restored to the state of revision 20261020_30 and
    # 20261019_29, which is what the application code already expected.
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

    op.execute(
        "DROP POLICY IF EXISTS cold_chain_violations_tenant_insert ON cold_chain_violations"
    )
    op.execute(
        """
        CREATE POLICY cold_chain_violations_tenant_insert ON cold_chain_violations
        FOR INSERT
        WITH CHECK (
            public.app_current_role() = 'system_admin'
            OR EXISTS (
                SELECT 1 FROM public.shipments AS s
                WHERE s.id = cold_chain_violations.shipment_id
                  AND s.organization_id = public.app_current_organization_id()
            )
        )
        """
    )

    op.execute("DROP POLICY IF EXISTS shipments_read ON shipments")
    op.execute(
        """
        CREATE POLICY shipments_read ON shipments
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
        )
        """
    )

    op.execute(
        "DROP POLICY IF EXISTS temperature_hourly_aggregates_read_tenant_or_auditor "
        "ON temperature_hourly_aggregates"
    )
    op.execute(
        """
        CREATE POLICY temperature_hourly_aggregates_read_tenant_or_auditor
        ON temperature_hourly_aggregates
        FOR SELECT
        USING (
            EXISTS (
                SELECT 1 FROM public.shipments AS s
                WHERE s.id = temperature_hourly_aggregates.shipment_id
                  AND (
                      s.organization_id = public.app_current_organization_id()
                      OR public.app_current_role() IN ('inspector', 'system_admin')
                  )
            )
        )
        """
    )
