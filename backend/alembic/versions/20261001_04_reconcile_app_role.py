"""Reconcile least-privilege grants for the application database role.

Revision ID: 20261001_04
Revises: 20260929_03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.config import settings

revision: str = "20261001_04"
down_revision: str | None = "20260929_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _application_role() -> str | None:
    bind = op.get_bind()
    role_exists = bind.execute(
        sa.text(
            "SELECT 1 FROM pg_catalog.pg_roles "
            "WHERE rolname = :role AND :role <> current_user"
        ),
        {"role": settings.DB_USER},
    ).scalar()
    if not role_exists:
        return None
    return bind.dialect.identifier_preparer.quote(settings.DB_USER)


def upgrade() -> None:
    role = _application_role()
    if role is None:
        return

    # Re-run these idempotent grants so existing staging databases receive the
    # same least-privilege role permissions as a fresh migration.
    op.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
    op.execute(f"REVOKE CREATE ON SCHEMA public FROM PUBLIC, {role}")
    op.execute(f"GRANT SELECT ON organizations, roles, users, sessions TO {role}")
    op.execute(f"GRANT UPDATE (failed_login_attempts, locked_until) ON users TO {role}")
    op.execute(f"GRANT INSERT ON sessions TO {role}")
    op.execute(f"GRANT UPDATE (revoked_at) ON sessions TO {role}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON farms TO {role}")

    for table in ("organizations", "users", "sessions", "farms"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    # The grants originate in earlier migrations as well; downgrading this
    # reconciliation migration must not remove permissions expected by N3-5/7.
    pass
