"""Apply tenant isolation to identity tables for N3-6.

Revision ID: 20260929_02
Revises: 20260929_01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260929_02"
down_revision: str | None = "20260929_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("organizations", "users", "sessions"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY organizations_visible_to_tenant_or_auth ON organizations
        FOR SELECT
        USING (
            id = NULLIF(current_setting('app.current_organization', true), '')::uuid
            OR id = NULLIF(current_setting('app.login_organization', true), '')::uuid
            OR id IN (
                SELECT u.organization_id FROM users AS u
                WHERE u.id IN (
                    SELECT s.user_id FROM sessions AS s
                    WHERE s.token_hash = NULLIF(
                        current_setting('app.session_token_hash', true), ''
                    )
                )
            )
        )
        """)
    op.execute("""
        CREATE POLICY users_visible_to_tenant_or_auth ON users
        FOR SELECT
        USING (
            organization_id = NULLIF(
                current_setting('app.current_organization', true), ''
            )::uuid
            OR email = NULLIF(current_setting('app.login_email', true), '')
            OR id IN (
                SELECT s.user_id FROM sessions AS s
                WHERE s.token_hash = NULLIF(
                    current_setting('app.session_token_hash', true), ''
                )
            )
        )
        """)
    op.execute("""
        CREATE POLICY users_update_tenant_or_auth ON users
        FOR UPDATE
        USING (
            organization_id = NULLIF(
                current_setting('app.current_organization', true), ''
            )::uuid
            OR email = NULLIF(current_setting('app.login_email', true), '')
            OR id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        WITH CHECK (
            organization_id = NULLIF(
                current_setting('app.current_organization', true), ''
            )::uuid
            OR email = NULLIF(current_setting('app.login_email', true), '')
            OR id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        """)
    op.execute("""
        CREATE POLICY sessions_visible_to_current_user_or_token ON sessions
        FOR SELECT
        USING (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
            OR token_hash = NULLIF(
                current_setting('app.session_token_hash', true), ''
            )
        )
        """)
    op.execute("""
        CREATE POLICY sessions_insert_current_user ON sessions
        FOR INSERT
        WITH CHECK (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        """)
    op.execute("""
        CREATE POLICY sessions_update_current_user_or_token ON sessions
        FOR UPDATE
        USING (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
            OR token_hash = NULLIF(
                current_setting('app.session_token_hash', true), ''
            )
        )
        WITH CHECK (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        """)


def downgrade() -> None:
    for policy, table in (
        ("sessions_update_current_user_or_token", "sessions"),
        ("sessions_insert_current_user", "sessions"),
        ("sessions_visible_to_current_user_or_token", "sessions"),
        ("users_update_tenant_or_auth", "users"),
        ("users_visible_to_tenant_or_auth", "users"),
        ("organizations_visible_to_tenant_or_auth", "organizations"),
    ):
        op.execute(f"DROP POLICY {policy} ON {table}")
    for table in ("organizations", "users", "sessions"):
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
