"""Upgrade admin@mocchau.vn to system_admin role and update RLS policies.

Revision ID: 20261007_12
Revises: 20261007_11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261007_12"
down_revision: str | None = "20261007_11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET role_code = 'system_admin',
            full_name = 'Trần Thị Hương (Quản trị viên Hệ thống)'
        WHERE email = 'admin@mocchau.vn';
        """
    )

    op.execute("DROP POLICY IF EXISTS farms_organization_isolation ON farms")
    op.execute(
        """
        CREATE POLICY farms_organization_isolation ON farms
        FOR ALL
        USING (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() = 'system_admin'
        )
        WITH CHECK (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() = 'system_admin'
        );
        """
    )

    op.execute(
        "DROP POLICY IF EXISTS organizations_visible_to_tenant_or_auth ON organizations"
    )
    op.execute(
        """
        CREATE POLICY organizations_visible_to_tenant_or_auth ON organizations
        FOR SELECT
        USING (
            id = public.app_current_organization_id()
            OR id IN (
                SELECT u.organization_id FROM public.users AS u
                WHERE u.email = NULLIF(current_setting('app.login_email', true), '')
            )
            OR public.app_current_role() = 'system_admin'
        );
        """
    )

    op.execute("DROP POLICY IF EXISTS users_visible_to_tenant_or_auth ON users")
    op.execute(
        """
        CREATE POLICY users_visible_to_tenant_or_auth ON users
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR email = NULLIF(current_setting('app.login_email', true), '')
            OR public.app_current_role() = 'system_admin'
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS users_visible_to_tenant_or_auth ON users")
    op.execute(
        """
        CREATE POLICY users_visible_to_tenant_or_auth ON users
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR email = NULLIF(current_setting('app.login_email', true), '')
        );
        """
    )

    op.execute(
        "DROP POLICY IF EXISTS organizations_visible_to_tenant_or_auth ON organizations"
    )
    op.execute(
        """
        CREATE POLICY organizations_visible_to_tenant_or_auth ON organizations
        FOR SELECT
        USING (
            id = public.app_current_organization_id()
            OR id IN (
                SELECT u.organization_id FROM public.users AS u
                WHERE u.email = NULLIF(current_setting('app.login_email', true), '')
            )
        );
        """
    )

    op.execute(
        """
        UPDATE users
        SET role_code = 'organization_admin',
            full_name = 'Trần Thị Hương (Quản trị HTX Mộc Châu)'
        WHERE email = 'admin@mocchau.vn';
        """
    )

    op.execute("DROP POLICY IF EXISTS farms_organization_isolation ON farms")
    op.execute(
        """
        CREATE POLICY farms_organization_isolation ON farms
        FOR ALL
        USING (organization_id = public.app_current_organization_id())
        WITH CHECK (organization_id = public.app_current_organization_id());
        """
    )
