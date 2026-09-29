"""Enforce organization ownership for farms at the database layer.

Revision ID: 20260929_03
Revises: 20260929_02
Create Date: 2026-09-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260929_03"
down_revision: str | None = "20260929_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("REVOKE CONNECT ON DATABASE ttcs_db FROM PUBLIC")
    op.execute("GRANT CONNECT ON DATABASE ttcs_db TO ttcs_app")
    op.execute("GRANT USAGE ON SCHEMA public TO ttcs_app")
    op.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC, ttcs_app")
    op.execute("ALTER TABLE farms ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE farms FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY farms_organization_isolation ON farms
        USING (
            organization_id = NULLIF(
                current_setting('app.current_organization', true), ''
            )::uuid
        )
        WITH CHECK (
            organization_id = NULLIF(
                current_setting('app.current_organization', true), ''
            )::uuid
        )
        """
    )
    op.execute("GRANT SELECT ON organizations, roles, users, sessions TO ttcs_app")
    op.execute("GRANT INSERT ON organizations TO ttcs_app")
    op.execute("GRANT INSERT, UPDATE ON users TO ttcs_app")
    op.execute("GRANT INSERT, UPDATE, DELETE ON sessions TO ttcs_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON farms TO ttcs_app")


def downgrade() -> None:
    op.execute("REVOKE SELECT, INSERT, UPDATE ON farms FROM ttcs_app")
    op.execute("REVOKE INSERT ON organizations FROM ttcs_app")
    op.execute("REVOKE INSERT, UPDATE ON users FROM ttcs_app")
    op.execute("REVOKE INSERT, UPDATE, DELETE ON sessions FROM ttcs_app")
    op.execute("REVOKE SELECT ON organizations, roles, users, sessions FROM ttcs_app")
    op.execute("DROP POLICY farms_organization_isolation ON farms")
    op.execute("ALTER TABLE farms NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE farms DISABLE ROW LEVEL SECURITY")
    op.execute("REVOKE USAGE ON SCHEMA public FROM ttcs_app")
    op.execute("REVOKE CONNECT ON DATABASE ttcs_db FROM ttcs_app")
    op.execute("GRANT CONNECT ON DATABASE ttcs_db TO PUBLIC")
