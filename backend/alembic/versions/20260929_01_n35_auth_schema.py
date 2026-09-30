"""Create organization, role, user, and session tables for N3-5.

Revision ID: 20260929_01
Revises:
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

revision: str = "20260929_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("organization_type", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "organization_type IN ('farm', 'cooperative', 'transport', "
            "'distribution', 'inspection', 'administration')",
            name="ck_organizations_type",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "roles",
        sa.Column("code", sa.String(length=48), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_code", sa.String(length=48), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "email = lower(btrim(email))", name="ck_users_email_normalized"
        ),
        sa.CheckConstraint(
            "failed_login_attempts >= 0",
            name="ck_users_failed_login_attempts_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["role_code"], ["roles.code"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])

    op.execute(
        "INSERT INTO roles (code, name) VALUES "
        "('grower', 'Grower'), "
        "('cooperative', 'Cooperative'), "
        "('transporter', 'Transporter'), "
        "('distributor', 'Distributor'), "
        "('inspector', 'Inspector'), "
        "('organization_admin', 'Organization admin'), "
        "('system_admin', 'System admin') "
        "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name"
    )

    bind = op.get_bind()
    role_exists = bind.execute(
        sa.text(
            "SELECT 1 FROM pg_catalog.pg_roles "
            "WHERE rolname = :role AND :role <> current_user"
        ),
        {"role": settings.DB_USER},
    ).scalar()
    if role_exists:
        role = bind.dialect.identifier_preparer.quote(settings.DB_USER)
        op.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
        op.execute(f"REVOKE CREATE ON SCHEMA public FROM PUBLIC, {role}")
        op.execute(f"GRANT SELECT ON organizations, roles, users, sessions TO {role}")
        op.execute(
            f"GRANT UPDATE (failed_login_attempts, locked_until) ON users TO {role}"
        )
        op.execute(f"GRANT INSERT ON sessions TO {role}")
        op.execute(f"GRANT UPDATE (revoked_at) ON sessions TO {role}")


def downgrade() -> None:
    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_users_organization_id", table_name="users")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("organizations")
