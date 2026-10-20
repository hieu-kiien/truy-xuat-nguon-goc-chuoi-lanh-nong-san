"""Add the in-app notification centre (N3-56).

Notifications are produced by the service layer and stored per recipient, so
the unread badge and the read state survive a reload.

Revision ID: 20261021_34
Revises: 20261021_33
Create Date: 2026-10-21 10:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "20261021_34"
down_revision: str | Sequence[str] | None = "20261021_33"
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
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("source_key", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("link_path", sa.String(length=255), nullable=False),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind IN ('handover_pending', 'recall_affected', 'cold_chain_violation')",
            name="ck_notifications_kind",
        ),
        sa.CheckConstraint(
            "length(btrim(title)) > 0", name="ck_notifications_title_nonblank"
        ),
        sa.CheckConstraint(
            "length(btrim(link_path)) > 0", name="ck_notifications_link_nonblank"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "recipient_user_id",
            "source_key",
            name="uq_notifications_recipient_source",
        ),
    )
    op.create_index(
        "ix_notifications_recipient_created",
        "notifications",
        ["recipient_user_id", "created_at"],
    )
    op.create_index(
        "ix_notifications_recipient_unread",
        "notifications",
        ["recipient_user_id"],
        unique=False,
        postgresql_where=sa.text("read_at IS NULL"),
    )
    op.create_index(
        "ix_notifications_lot_id",
        "notifications",
        ["lot_id"],
    )

    op.execute("ALTER TABLE notifications ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY notifications_select_own ON notifications
        FOR SELECT
        USING (
            recipient_user_id = public.app_current_user_id()
        )
        """
    )
    op.execute(
        """
        CREATE POLICY notifications_insert_tenant ON notifications
        FOR INSERT
        WITH CHECK (
            organization_id = public.app_current_organization_id()
        )
        """
    )
    op.execute(
        """
        CREATE POLICY notifications_update_own ON notifications
        FOR UPDATE
        USING (
            recipient_user_id = public.app_current_user_id()
        )
        WITH CHECK (
            recipient_user_id = public.app_current_user_id()
        )
        """
    )

    role = _application_role()
    if role:
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON notifications TO {role}")
        op.execute(f"REVOKE DELETE ON notifications FROM {role}")


def downgrade() -> None:
    role = _application_role()
    if role:
        op.execute(f"REVOKE SELECT, INSERT, UPDATE ON notifications FROM {role}")

    op.execute("DROP POLICY IF EXISTS notifications_update_own ON notifications")
    op.execute("DROP POLICY IF EXISTS notifications_insert_tenant ON notifications")
    op.execute("DROP POLICY IF EXISTS notifications_select_own ON notifications")
    op.execute("ALTER TABLE notifications DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_notifications_lot_id", table_name="notifications")
    op.drop_index("ix_notifications_recipient_unread", table_name="notifications")
    op.drop_index("ix_notifications_recipient_created", table_name="notifications")
    op.drop_table("notifications")
