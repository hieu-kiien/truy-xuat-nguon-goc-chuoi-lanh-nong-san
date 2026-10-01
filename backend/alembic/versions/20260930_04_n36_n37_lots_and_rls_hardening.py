"""Add real organization-scoped lots and bind RLS to authenticated sessions.

Revision ID: 20260930_04
Revises: 20260929_03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

revision: str = "20260930_04"
down_revision: str | None = "20260929_03"
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


def _create_session_context_functions() -> None:
    op.execute(
        """
        CREATE FUNCTION public.app_current_user_id()
        RETURNS uuid
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT s.user_id
            FROM public.sessions AS s
            JOIN public.users AS u ON u.id = s.user_id
            JOIN public.organizations AS o ON o.id = u.organization_id
            WHERE s.token_hash = NULLIF(
                    current_setting('app.session_token_hash', true), ''
                )
              AND s.revoked_at IS NULL
              AND s.expires_at > CURRENT_TIMESTAMP
              AND u.is_active
              AND o.is_active
            LIMIT 1
        $function$
        """
    )
    op.execute(
        """
        CREATE FUNCTION public.app_current_organization_id()
        RETURNS uuid
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT u.organization_id
            FROM public.users AS u
            WHERE u.id = public.app_current_user_id()
            LIMIT 1
        $function$
        """
    )
    op.execute(
        """
        CREATE FUNCTION public.app_current_role()
        RETURNS text
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT u.role_code
            FROM public.users AS u
            WHERE u.id = public.app_current_user_id()
            LIMIT 1
        $function$
        """
    )
    op.execute("REVOKE ALL ON FUNCTION public.app_current_user_id() FROM PUBLIC")
    op.execute(
        "REVOKE ALL ON FUNCTION public.app_current_organization_id() FROM PUBLIC"
    )
    op.execute("REVOKE ALL ON FUNCTION public.app_current_role() FROM PUBLIC")

    role = _application_role()
    if role:
        op.execute(f"GRANT EXECUTE ON FUNCTION public.app_current_user_id() TO {role}")
        op.execute(
            f"GRANT EXECUTE ON FUNCTION public.app_current_organization_id() TO {role}"
        )
        op.execute(f"GRANT EXECUTE ON FUNCTION public.app_current_role() TO {role}")


def _replace_identity_policies_with_authenticated_context() -> None:
    op.execute("DROP POLICY organizations_visible_to_tenant_or_auth ON organizations")
    op.execute("DROP POLICY users_visible_to_tenant_or_auth ON users")
    op.execute("DROP POLICY users_update_tenant_or_auth ON users")
    op.execute("DROP POLICY sessions_visible_to_current_user_or_token ON sessions")
    op.execute("DROP POLICY sessions_insert_current_user ON sessions")
    op.execute("DROP POLICY sessions_update_current_user_or_token ON sessions")

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
        )
        """
    )
    op.execute(
        """
        CREATE POLICY users_visible_to_tenant_or_auth ON users
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR email = NULLIF(current_setting('app.login_email', true), '')
        )
        """
    )
    op.execute(
        """
        CREATE POLICY users_update_tenant_or_auth ON users
        FOR UPDATE
        USING (
            organization_id = public.app_current_organization_id()
            OR email = NULLIF(current_setting('app.login_email', true), '')
        )
        WITH CHECK (
            organization_id = public.app_current_organization_id()
            OR email = NULLIF(current_setting('app.login_email', true), '')
        )
        """
    )
    op.execute(
        """
        CREATE POLICY sessions_visible_to_current_user_or_token ON sessions
        FOR SELECT
        USING (
            user_id = public.app_current_user_id()
            OR token_hash = NULLIF(
                current_setting('app.session_token_hash', true), ''
            )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY sessions_insert_current_user ON sessions
        FOR INSERT
        WITH CHECK (
            user_id IN (
                SELECT u.id FROM public.users AS u
                WHERE u.email = NULLIF(current_setting('app.login_email', true), '')
            )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY sessions_update_current_user_or_token ON sessions
        FOR UPDATE
        USING (
            user_id = public.app_current_user_id()
            OR token_hash = NULLIF(
                current_setting('app.session_token_hash', true), ''
            )
        )
        WITH CHECK (
            user_id = public.app_current_user_id()
            OR token_hash = NULLIF(
                current_setting('app.session_token_hash', true), ''
            )
        )
        """
    )


def upgrade() -> None:
    op.drop_constraint("ck_farms_area_positive", "farms", type_="check")
    op.create_check_constraint(
        "ck_farms_area_positive",
        "farms",
        "area_ha > 0 AND area_ha < 'Infinity'::numeric",
    )
    op.create_check_constraint(
        "ck_farms_name_nonblank", "farms", "length(btrim(name)) > 0"
    )
    op.create_unique_constraint(
        "uq_farms_id_organization_id", "farms", ["id", "organization_id"]
    )

    op.create_table(
        "lots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_lots_name_nonblank"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_lots_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id", "organization_id"],
            ["farms.id", "farms.organization_id"],
            name="fk_lots_farm_same_organization",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lots_organization_id", "lots", ["organization_id"])
    op.create_index("ix_lots_farm_id", "lots", ["farm_id"])

    _create_session_context_functions()
    _replace_identity_policies_with_authenticated_context()

    op.execute("DROP POLICY farms_organization_isolation ON farms")
    op.execute(
        """
        CREATE POLICY farms_organization_isolation ON farms
        FOR ALL
        USING (organization_id = public.app_current_organization_id())
        WITH CHECK (organization_id = public.app_current_organization_id())
        """
    )
    op.execute("ALTER TABLE lots ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY lots_read_tenant_or_inspector ON lots
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() = 'inspector'
        )
        """
    )

    role = _application_role()
    if role:
        op.execute(f"REVOKE INSERT, UPDATE, DELETE ON lots FROM {role}")
        op.execute(f"GRANT SELECT ON lots TO {role}")


def downgrade() -> None:
    role = _application_role()
    if role:
        op.execute(f"REVOKE SELECT ON lots FROM {role}")
        op.execute(
            f"REVOKE EXECUTE ON FUNCTION public.app_current_user_id() FROM {role}"
        )
        op.execute(
            "REVOKE EXECUTE ON FUNCTION "
            f"public.app_current_organization_id() FROM {role}"
        )
        op.execute(f"REVOKE EXECUTE ON FUNCTION public.app_current_role() FROM {role}")

    op.execute("DROP POLICY lots_read_tenant_or_inspector ON lots")
    op.execute("ALTER TABLE lots NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE lots DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_lots_farm_id", table_name="lots")
    op.drop_index("ix_lots_organization_id", table_name="lots")
    op.drop_table("lots")

    op.execute("DROP POLICY farms_organization_isolation ON farms")
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

    for policy, table in (
        ("sessions_update_current_user_or_token", "sessions"),
        ("sessions_insert_current_user", "sessions"),
        ("sessions_visible_to_current_user_or_token", "sessions"),
        ("users_update_tenant_or_auth", "users"),
        ("users_visible_to_tenant_or_auth", "users"),
        ("organizations_visible_to_tenant_or_auth", "organizations"),
    ):
        op.execute(f"DROP POLICY {policy} ON {table}")

    op.execute(
        """
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
        """
    )
    op.execute(
        """
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
        """
    )
    op.execute(
        """
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
        """
    )
    op.execute(
        """
        CREATE POLICY sessions_visible_to_current_user_or_token ON sessions
        FOR SELECT
        USING (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
            OR token_hash = NULLIF(
                current_setting('app.session_token_hash', true), ''
            )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY sessions_insert_current_user ON sessions
        FOR INSERT
        WITH CHECK (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        """
    )
    op.execute(
        """
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
        """
    )

    op.execute("DROP FUNCTION public.app_current_role()")
    op.execute("DROP FUNCTION public.app_current_organization_id()")
    op.execute("DROP FUNCTION public.app_current_user_id()")
    op.drop_constraint("uq_farms_id_organization_id", "farms", type_="unique")
    op.drop_constraint("ck_farms_name_nonblank", "farms", type_="check")
    op.drop_constraint("ck_farms_area_positive", "farms", type_="check")
    op.create_check_constraint(
        "ck_farms_area_positive",
        "farms",
        "area_ha > 0 AND area_ha <> 'NaN'::numeric",
    )
