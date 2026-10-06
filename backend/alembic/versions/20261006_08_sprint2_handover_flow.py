"""Add current lot custody and append-only organization handovers.

Revision ID: 20261006_08
Revises: 20261006_07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

revision: str = "20261006_08"
down_revision: str | None = "20261006_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


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
    op.add_column(
        "lots",
        sa.Column("current_holder_organization_id", postgresql.UUID(as_uuid=True)),
    )
    op.add_column(
        "lots",
        sa.Column(
            "remaining_quantity", sa.Numeric(precision=14, scale=3), nullable=True
        ),
    )
    op.add_column(
        "lots",
        sa.Column(
            "status",
            sa.String(length=24),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
    )
    op.execute(
        "UPDATE lots SET current_holder_organization_id = organization_id, "
        "remaining_quantity = COALESCE(quantity, 0)"
    )
    op.alter_column("lots", "current_holder_organization_id", nullable=False)
    op.alter_column("lots", "remaining_quantity", nullable=False)
    op.create_foreign_key(
        "fk_lots_current_holder_organization_id_organizations",
        "lots",
        "organizations",
        ["current_holder_organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_lots_remaining_quantity_range",
        "lots",
        "remaining_quantity >= 0 AND "
        "(quantity IS NULL OR remaining_quantity <= quantity)",
    )
    op.create_check_constraint(
        "ck_lots_status_supported",
        "lots",
        "status IN ('active', 'pending_handover', 'closed')",
    )
    op.create_index(
        "ix_lots_holder_harvested_on",
        "lots",
        ["current_holder_organization_id", "harvested_on", "id"],
    )

    op.create_table(
        "handovers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resolved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "from_organization_id <> to_organization_id",
            name="ck_handovers_different_organizations",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')",
            name="ck_handovers_status_supported",
        ),
        sa.CheckConstraint(
            "rejection_reason IS NULL OR length(btrim(rejection_reason)) >= 10",
            name="ck_handovers_rejection_reason_length",
        ),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["from_organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["to_organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_handovers_one_pending_per_lot",
        "handovers",
        ["lot_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_handovers_recipient_status",
        "handovers",
        ["to_organization_id", "status"],
    )
    op.create_index(
        "ix_handovers_sender_status",
        "handovers",
        ["from_organization_id", "status"],
    )

    op.execute("DROP POLICY lots_read_tenant_or_inspector ON lots")
    op.execute("DROP POLICY lots_insert_tenant ON lots")
    op.execute(
        """
        CREATE POLICY lots_read_tenant_or_inspector ON lots
        FOR SELECT
        USING (
            current_holder_organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
            OR EXISTS (
                SELECT 1 FROM public.handovers AS h
                WHERE h.lot_id = lots.id
                  AND h.to_organization_id = public.app_current_organization_id()
                  AND h.status = 'pending'
            )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY lots_insert_tenant ON lots
        FOR INSERT
        WITH CHECK (
            organization_id = public.app_current_organization_id()
            AND current_holder_organization_id = public.app_current_organization_id()
        )
        """
    )
    op.execute(
        """
        CREATE POLICY lots_update_holder ON lots
        FOR UPDATE
        USING (
            current_holder_organization_id = public.app_current_organization_id()
            OR EXISTS (
                SELECT 1 FROM public.handovers AS h
                WHERE h.lot_id = lots.id
                  AND h.to_organization_id = public.app_current_organization_id()
                  AND h.status = 'pending'
            )
        )
        WITH CHECK (
            current_holder_organization_id = public.app_current_organization_id()
            OR EXISTS (
                SELECT 1 FROM public.handovers AS h
                WHERE h.lot_id = lots.id
                  AND h.to_organization_id = public.app_current_organization_id()
                  AND h.status = 'pending'
            )
        )
        """
    )

    op.execute("DROP POLICY events_read_tenant_or_inspector ON events")
    op.execute(
        """
        CREATE POLICY events_read_tenant_or_inspector ON events
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
            OR EXISTS (
                SELECT 1 FROM public.lots AS l
                WHERE l.id = events.lot_id
                  AND (
                      l.current_holder_organization_id = public.app_current_organization_id()
                      OR EXISTS (
                          SELECT 1 FROM public.handovers AS h
                          WHERE h.lot_id = l.id
                            AND h.to_organization_id = public.app_current_organization_id()
                            AND h.status = 'pending'
                      )
                  )
            )
        )
        """
    )
    op.execute("DROP POLICY events_insert_tenant ON events")
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
            )
        )
        """
    )

    op.execute("ALTER TABLE handovers ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY handovers_select_parties ON handovers
        FOR SELECT
        USING (
            from_organization_id = public.app_current_organization_id()
            OR to_organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
        )
        """
    )
    op.execute(
        """
        CREATE POLICY handovers_insert_sender ON handovers
        FOR INSERT
        WITH CHECK (
            from_organization_id = public.app_current_organization_id()
            AND status = 'pending'
        )
        """
    )
    op.execute(
        """
        CREATE POLICY handovers_update_recipient ON handovers
        FOR UPDATE
        USING (
            to_organization_id = public.app_current_organization_id()
            AND status = 'pending'
        )
        WITH CHECK (
            to_organization_id = public.app_current_organization_id()
            AND status IN ('accepted', 'rejected')
        )
        """
    )
    op.execute(
        """
        CREATE POLICY organizations_active_for_handover ON organizations
        FOR SELECT
        USING (public.app_current_user_id() IS NOT NULL AND is_active)
        """
    )

    role = _application_role()
    if role:
        op.execute(
            f"GRANT UPDATE (current_holder_organization_id, status) ON lots TO {role}"
        )
        op.execute(f"GRANT SELECT, INSERT ON handovers TO {role}")
        op.execute(
            "GRANT UPDATE (status, resolved_at, resolved_by_user_id, rejection_reason) "
            f"ON handovers TO {role}"
        )


def downgrade() -> None:
    role = _application_role()
    if role:
        op.execute(
            f"REVOKE UPDATE (current_holder_organization_id, status) ON lots FROM {role}"
        )
        op.execute(
            "REVOKE UPDATE (status, resolved_at, resolved_by_user_id, rejection_reason) "
            f"ON handovers FROM {role}"
        )
        op.execute(f"REVOKE SELECT, INSERT ON handovers FROM {role}")

    op.execute("DROP POLICY IF EXISTS organizations_active_for_handover ON organizations")
    op.execute("DROP POLICY IF EXISTS handovers_update_recipient ON handovers")
    op.execute("DROP POLICY IF EXISTS handovers_insert_sender ON handovers")
    op.execute("DROP POLICY IF EXISTS handovers_select_parties ON handovers")
    op.execute("ALTER TABLE handovers NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE handovers DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS lots_update_holder ON lots")
    op.execute("DROP POLICY lots_insert_tenant ON lots")
    op.execute("DROP POLICY lots_read_tenant_or_inspector ON lots")
    op.execute(
        """
        CREATE POLICY lots_read_tenant_or_inspector ON lots
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() = 'inspector'
        )
        """
    )
    op.execute(
        """
        CREATE POLICY lots_insert_tenant ON lots
        FOR INSERT
        WITH CHECK (organization_id = public.app_current_organization_id())
        """
    )
    op.execute("DROP POLICY events_insert_tenant ON events")
    op.execute(
        """
        CREATE POLICY events_insert_tenant ON events
        FOR INSERT
        WITH CHECK (organization_id = public.app_current_organization_id())
        """
    )
    op.execute("DROP POLICY events_read_tenant_or_inspector ON events")
    op.execute(
        """
        CREATE POLICY events_read_tenant_or_inspector ON events
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() = 'inspector'
        )
        """
    )

    op.drop_index("ix_handovers_sender_status", table_name="handovers")
    op.drop_index("ix_handovers_recipient_status", table_name="handovers")
    op.drop_index("uq_handovers_one_pending_per_lot", table_name="handovers")
    op.drop_table("handovers")
    op.drop_index("ix_lots_holder_harvested_on", table_name="lots")
    op.drop_constraint("ck_lots_status_supported", "lots", type_="check")
    op.drop_constraint(
        "ck_lots_remaining_quantity_range", "lots", type_="check"
    )
    op.drop_constraint(
        "fk_lots_current_holder_organization_id_organizations",
        "lots",
        type_="foreignkey",
    )
    op.drop_column("lots", "status")
    op.drop_column("lots", "remaining_quantity")
    op.drop_column("lots", "current_holder_organization_id")
