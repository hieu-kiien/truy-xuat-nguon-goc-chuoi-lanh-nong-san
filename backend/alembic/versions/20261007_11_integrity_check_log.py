"""Persist append-only event-chain verification results.

Revision ID: 20261007_11
Revises: 20261007_10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

revision: str = "20261007_11"
down_revision: str | None = "20261007_10"
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
    op.create_table(
        "integrity_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checked_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("valid", sa.Boolean(), nullable=False),
        sa.Column("checked_events", sa.Integer(), nullable=False),
        sa.Column("first_invalid_sequence", sa.Integer(), nullable=True),
        sa.Column(
            "issues",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.CheckConstraint(
            "checked_events >= 0", name="ck_integrity_checks_event_count"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["checked_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_integrity_checks_lot_checked",
        "integrity_checks",
        ["lot_id", "checked_at"],
    )
    op.create_index(
        "ix_integrity_checks_organization_checked",
        "integrity_checks",
        ["organization_id", "checked_at"],
    )

    op.execute("ALTER TABLE integrity_checks ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE integrity_checks FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY integrity_checks_read_tenant_or_auditor ON integrity_checks
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
        )
        """
    )
    op.execute(
        """
        CREATE POLICY integrity_checks_insert_tenant ON integrity_checks
        FOR INSERT
        WITH CHECK (
            organization_id = public.app_current_organization_id()
            AND public.app_current_role() IN ('inspector', 'system_admin')
        )
        """
    )

    role = _application_role()
    if role:
        op.execute(f"REVOKE UPDATE, DELETE ON integrity_checks FROM {role}")
        op.execute(f"GRANT SELECT, INSERT ON integrity_checks TO {role}")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.prevent_integrity_check_mutation()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            RAISE EXCEPTION 'Integrity check records are append-only.'
                USING ERRCODE = 'integrity_constraint_violation';
        END;
        $function$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_integrity_checks_prevent_update
            BEFORE UPDATE ON integrity_checks
            FOR EACH ROW
            EXECUTE FUNCTION public.prevent_integrity_check_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_integrity_checks_prevent_delete
            BEFORE DELETE ON integrity_checks
            FOR EACH ROW
            EXECUTE FUNCTION public.prevent_integrity_check_mutation();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_integrity_checks_prevent_delete ON integrity_checks"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_integrity_checks_prevent_update ON integrity_checks"
    )
    op.execute("DROP FUNCTION IF EXISTS public.prevent_integrity_check_mutation()")

    role = _application_role()
    if role:
        op.execute(f"REVOKE SELECT, INSERT ON integrity_checks FROM {role}")

    op.execute(
        "DROP POLICY IF EXISTS integrity_checks_insert_tenant ON integrity_checks"
    )
    op.execute(
        "DROP POLICY IF EXISTS integrity_checks_read_tenant_or_auditor ON integrity_checks"
    )
    op.execute("ALTER TABLE integrity_checks NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE integrity_checks DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_integrity_checks_organization_checked", table_name="integrity_checks"
    )
    op.drop_index("ix_integrity_checks_lot_checked", table_name="integrity_checks")
    op.drop_table("integrity_checks")
