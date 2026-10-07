"""Let auditors resolve names for organizations that hold visible lots."""

from collections.abc import Sequence

from alembic import op

revision: str = "20261007_14"
down_revision: str | None = "20261007_13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP POLICY organizations_visible_to_tenant_or_auth ON organizations")
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
            OR public.app_current_role() IN ('system_admin', 'inspector')
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY organizations_visible_to_tenant_or_auth ON organizations")
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
