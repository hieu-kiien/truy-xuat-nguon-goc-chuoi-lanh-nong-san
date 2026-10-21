"""Add the e-mail outbox and the organization contact address (N3-57, N3-30).

Every outbound e-mail is recorded before it leaves the system, so a staging
environment without an SMTP server still produces evidence that the message
was produced.

Revision ID: 20261021_35
Revises: 20261021_34
Create Date: 2026-10-21 11:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "20261021_35"
down_revision: str | Sequence[str] | None = "20261021_34"
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
    # 1. Every organization can publish one contact address for official notices.
    op.add_column(
        "organizations",
        sa.Column("contact_email", sa.String(length=320), nullable=True),
    )
    op.create_check_constraint(
        "ck_organizations_contact_email",
        "organizations",
        "contact_email IS NULL OR contact_email = lower(btrim(contact_email))",
    )

    # 2. Only the administrator of an organization may publish its contact
    #    address, and only for its own organization.
    op.execute(
        """
        CREATE POLICY organizations_update_contact_email ON organizations
        FOR UPDATE
        USING (
            id = public.app_current_organization_id()
            AND public.app_current_role() IN ('organization_admin', 'system_admin')
        )
        WITH CHECK (
            id = public.app_current_organization_id()
            AND public.app_current_role() IN ('organization_admin', 'system_admin')
        )
        """
    )

    # 3. Durable record of every outbound message.
    op.create_table(
        "email_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recipient_email", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(length=48), nullable=False),
        sa.Column("related_id", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'recorded'"),
            nullable=False,
        ),
        sa.Column(
            "attempts", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('sent', 'recorded', 'failed')", name="ck_email_outbox_status"
        ),
        sa.CheckConstraint(
            "attempts >= 0", name="ck_email_outbox_attempts_nonnegative"
        ),
        sa.CheckConstraint(
            "length(btrim(recipient_email)) > 0",
            name="ck_email_outbox_recipient_nonblank",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_email_outbox_organization_created",
        "email_outbox",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "ix_email_outbox_kind",
        "email_outbox",
        ["kind"],
    )

    op.execute("ALTER TABLE email_outbox ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY email_outbox_read_tenant_or_auditor ON email_outbox
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
        )
        """
    )
    op.execute(
        """
        CREATE POLICY email_outbox_insert_tenant ON email_outbox
        FOR INSERT
        WITH CHECK (
            organization_id = public.app_current_organization_id()
        )
        """
    )
    op.execute(
        """
        CREATE POLICY email_outbox_update_tenant ON email_outbox
        FOR UPDATE
        USING (
            organization_id = public.app_current_organization_id()
        )
        WITH CHECK (
            organization_id = public.app_current_organization_id()
        )
        """
    )

    role = _application_role()
    if role:
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON email_outbox TO {role}")
        op.execute(f"REVOKE DELETE ON email_outbox FROM {role}")
        op.execute(f"GRANT UPDATE (contact_email) ON organizations TO {role}")


def downgrade() -> None:
    role = _application_role()
    if role:
        op.execute(f"REVOKE SELECT, INSERT, UPDATE ON email_outbox FROM {role}")
        op.execute(f"REVOKE UPDATE (contact_email) ON organizations FROM {role}")

    op.execute(
        "DROP POLICY IF EXISTS organizations_update_contact_email ON organizations"
    )
    op.execute("DROP POLICY IF EXISTS email_outbox_update_tenant ON email_outbox")
    op.execute("DROP POLICY IF EXISTS email_outbox_insert_tenant ON email_outbox")
    op.execute(
        "DROP POLICY IF EXISTS email_outbox_read_tenant_or_auditor ON email_outbox"
    )
    op.execute("ALTER TABLE email_outbox DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_email_outbox_kind", table_name="email_outbox")
    op.drop_index("ix_email_outbox_organization_created", table_name="email_outbox")
    op.drop_table("email_outbox")

    op.drop_constraint("ck_organizations_contact_email", "organizations", type_="check")
    op.drop_column("organizations", "contact_email")
