"""Add periodic integrity scanning support (N3-74).

Adds a provenance column to integrity checks, lets the privileged maintenance
role record checks that no human performed, and creates the alert table that
the administrator view reads.

Revision ID: 20261021_33
Revises: 20261020_32
Create Date: 2026-10-21 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "20261021_33"
down_revision: str | Sequence[str] | None = "20261020_32"
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


def _application_role_literal() -> str:
    """Return the application role name as a SQL string literal."""
    return "'" + settings.DB_USER.replace("'", "''") + "'"


def upgrade() -> None:
    app_role = _application_role()

    # 1. A scheduled check has no human behind it, so the actor column becomes
    #    optional and a provenance column records who requested the check.
    op.alter_column(
        "integrity_checks",
        "checked_by_user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "integrity_checks",
        sa.Column(
            "checked_by_source",
            sa.String(length=16),
            server_default=sa.text("'user'"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_integrity_checks_source",
        "integrity_checks",
        "checked_by_source IN ('user', 'system')",
    )

    # 2. The maintenance role is the only role besides the application role that
    #    may write into integrity_checks. It has no session context, so the
    #    tenant policy can never match for it.
    if app_role:
        op.execute(
            f"""
            CREATE POLICY integrity_checks_insert_maintenance ON integrity_checks
            FOR INSERT WITH CHECK (
                current_user <> {_application_role_literal()}
            )
            """
        )

    # 3. Alerts raised when a lot's event chain is found broken.
    op.create_table(
        "integrity_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("first_invalid_sequence", sa.Integer(), nullable=True),
        sa.Column("issue_count", sa.Integer(), nullable=False),
        sa.Column("checked_events", sa.Integer(), nullable=False),
        sa.CheckConstraint("issue_count >= 1", name="ck_integrity_alerts_issue_count"),
        sa.CheckConstraint(
            "checked_events >= 0", name="ck_integrity_alerts_event_count"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_integrity_alerts_detected_at",
        "integrity_alerts",
        ["detected_at"],
    )
    op.create_index(
        "ix_integrity_alerts_lot_detected",
        "integrity_alerts",
        ["lot_id", "detected_at"],
    )
    op.create_index(
        "ix_integrity_alerts_organization_detected",
        "integrity_alerts",
        ["organization_id", "detected_at"],
    )

    op.execute("ALTER TABLE integrity_alerts ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY integrity_alerts_read_tenant_or_auditor ON integrity_alerts
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
        )
        """
    )
    if app_role:
        op.execute(
            f"""
            CREATE POLICY integrity_alerts_insert_maintenance ON integrity_alerts
            FOR INSERT WITH CHECK (
                current_user <> {_application_role_literal()}
            )
            """
        )

    if app_role:
        op.execute(f"GRANT SELECT ON integrity_alerts TO {app_role}")
        op.execute(f"REVOKE INSERT, UPDATE, DELETE ON integrity_alerts FROM {app_role}")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.prevent_integrity_alert_mutation()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            RAISE EXCEPTION 'Integrity alerts are append-only.'
                USING ERRCODE = 'integrity_constraint_violation';
        END;
        $function$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_integrity_alerts_prevent_update
            BEFORE UPDATE ON integrity_alerts
            FOR EACH ROW
            EXECUTE FUNCTION public.prevent_integrity_alert_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_integrity_alerts_prevent_delete
            BEFORE DELETE ON integrity_alerts
            FOR EACH ROW
            EXECUTE FUNCTION public.prevent_integrity_alert_mutation();
        """
    )


def downgrade() -> None:
    app_role = _application_role()

    op.execute(
        "DROP TRIGGER IF EXISTS trg_integrity_alerts_prevent_delete ON integrity_alerts"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_integrity_alerts_prevent_update ON integrity_alerts"
    )
    op.execute("DROP FUNCTION IF EXISTS public.prevent_integrity_alert_mutation()")

    if app_role:
        op.execute(f"REVOKE SELECT ON integrity_alerts FROM {app_role}")

    op.execute(
        "DROP POLICY IF EXISTS integrity_alerts_insert_maintenance ON integrity_alerts"
    )
    op.execute(
        "DROP POLICY IF EXISTS integrity_alerts_read_tenant_or_auditor ON integrity_alerts"
    )
    op.execute("ALTER TABLE integrity_alerts DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_integrity_alerts_organization_detected", table_name="integrity_alerts"
    )
    op.drop_index("ix_integrity_alerts_lot_detected", table_name="integrity_alerts")
    op.drop_index("ix_integrity_alerts_detected_at", table_name="integrity_alerts")
    op.drop_table("integrity_alerts")

    op.execute(
        "DROP POLICY IF EXISTS integrity_checks_insert_maintenance ON integrity_checks"
    )
    op.drop_constraint("ck_integrity_checks_source", "integrity_checks", type_="check")
    op.drop_column("integrity_checks", "checked_by_source")
    op.alter_column(
        "integrity_checks",
        "checked_by_user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
