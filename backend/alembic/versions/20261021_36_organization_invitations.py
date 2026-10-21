"""Add organization member invitations (N3-30).

An invitation carries a single-use token that expires after 72 hours. The
token is stored only as a hash; the raw value travels in the e-mail.

Accepting an invitation is a public operation, so it runs through a
``SECURITY DEFINER`` function: the function owns the tables and can create
the member account inside the inviting organization without widening the
application role.

Revision ID: 20261021_36
Revises: 20261021_35
Create Date: 2026-10-21 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "20261021_36"
down_revision: str | Sequence[str] | None = "20261021_35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INVITATION_TTL_HOURS = 72


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
        "organization_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role_code", sa.String(length=48), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "expires_at > created_at", name="ck_organization_invitations_expiry"
        ),
        sa.CheckConstraint(
            "email = lower(btrim(email))",
            name="ck_organization_invitations_email_normalized",
        ),
        sa.CheckConstraint(
            "accepted_at IS NULL OR revoked_at IS NULL",
            name="ck_organization_invitations_single_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["invited_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["accepted_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_organization_invitations_organization_created",
        "organization_invitations",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "ix_organization_invitations_token_hash",
        "organization_invitations",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "uq_organization_invitations_pending_email",
        "organization_invitations",
        ["organization_id", "email"],
        unique=True,
        postgresql_where=sa.text("accepted_at IS NULL AND revoked_at IS NULL"),
    )

    op.execute("ALTER TABLE organization_invitations ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY organization_invitations_read_tenant_or_auditor
        ON organization_invitations
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() IN ('inspector', 'system_admin')
        )
        """
    )
    op.execute(
        """
        CREATE POLICY organization_invitations_insert_admin
        ON organization_invitations
        FOR INSERT
        WITH CHECK (
            organization_id = public.app_current_organization_id()
            AND public.app_current_role() IN ('organization_admin', 'system_admin')
        )
        """
    )
    op.execute(
        """
        CREATE POLICY organization_invitations_update_admin
        ON organization_invitations
        FOR UPDATE
        USING (
            organization_id = public.app_current_organization_id()
            AND public.app_current_role() IN ('organization_admin', 'system_admin')
        )
        WITH CHECK (
            organization_id = public.app_current_organization_id()
            AND public.app_current_role() IN ('organization_admin', 'system_admin')
        )
        """
    )

    # Accepting an invitation is public: the function owns the tables so it can
    # create the member account inside the inviting organization.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_accept_invitation(
            p_token_hash text,
            p_password_hash text,
            p_full_name text
        )
        RETURNS TABLE (
            accepted_user_id uuid,
            accepted_organization_id uuid,
            accepted_role_code text,
            accepted_email text
        )
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            invitation public.organization_invitations%ROWTYPE;
            new_user public.users%ROWTYPE;
        BEGIN
            SELECT * INTO invitation
            FROM public.organization_invitations
            WHERE token_hash = p_token_hash
              AND accepted_at IS NULL
              AND revoked_at IS NULL
              AND expires_at > now();

            IF NOT FOUND THEN
                RAISE EXCEPTION 'Invitation is invalid or expired'
                    USING ERRCODE = 'no_data_found';
            END IF;

            IF EXISTS (SELECT 1 FROM public.users WHERE email = invitation.email) THEN
                RAISE EXCEPTION 'This address already has an account'
                    USING ERRCODE = 'unique_violation';
            END IF;

            INSERT INTO public.users (
                id, organization_id, role_code, email, full_name,
                password_hash, failed_login_attempts, locked_until, is_active
            )
            VALUES (
                gen_random_uuid(), invitation.organization_id, invitation.role_code,
                invitation.email, btrim(p_full_name), p_password_hash,
                0, NULL, true
            )
            RETURNING * INTO new_user;

            UPDATE public.organization_invitations
            SET accepted_at = now(), accepted_user_id = new_user.id
            WHERE id = invitation.id;

            RETURN QUERY
            SELECT new_user.id, invitation.organization_id,
                   invitation.role_code::text, invitation.email::text;
        END;
        $function$;
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION public.app_accept_invitation(text, text, text) FROM PUBLIC"
    )

    # The public invitation page runs without a session, so the row is read
    # through a function that owns the table.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_read_invitation(p_token_hash text)
        RETURNS TABLE (
            invitation_id uuid,
            invitation_organization_id uuid,
            invitation_organization_name text,
            invitation_email text,
            invitation_role_code text,
            invitation_expires_at timestamptz,
            invitation_accepted_at timestamptz,
            invitation_revoked_at timestamptz
        )
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        BEGIN
            RETURN QUERY
            SELECT i.id, i.organization_id, o.name::text, i.email::text,
                   i.role_code::text, i.expires_at, i.accepted_at, i.revoked_at
            FROM public.organization_invitations AS i
            JOIN public.organizations AS o ON o.id = i.organization_id
            WHERE i.token_hash = p_token_hash;
        END;
        $function$;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION public.app_read_invitation(text) FROM PUBLIC")

    # Deactivating a member is also a privileged operation: only the
    # administrator of the organization may do it, and only for its own members.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_deactivate_member(p_user_id uuid)
        RETURNS boolean
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            target_org uuid;
            caller_org uuid;
            caller_role text;
        BEGIN
            caller_org := public.app_current_organization_id();
            caller_role := public.app_current_role();

            IF caller_role NOT IN ('organization_admin', 'system_admin') THEN
                RAISE EXCEPTION 'Only an organization administrator may deactivate a member'
                    USING ERRCODE = 'insufficient_privilege';
            END IF;

            SELECT organization_id INTO target_org
            FROM public.users WHERE id = p_user_id;

            IF target_org IS NULL THEN
                RAISE EXCEPTION 'Unknown member'
                    USING ERRCODE = 'no_data_found';
            END IF;

            IF target_org <> caller_org AND caller_role <> 'system_admin' THEN
                RAISE EXCEPTION 'The member belongs to another organization'
                    USING ERRCODE = 'insufficient_privilege';
            END IF;

            UPDATE public.users SET is_active = false WHERE id = p_user_id;
            RETURN true;
        END;
        $function$;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION public.app_deactivate_member(uuid) FROM PUBLIC")

    role = _application_role()
    if role:
        op.execute(
            "GRANT EXECUTE ON FUNCTION public.app_read_invitation(text) TO " + role
        )
        op.execute(
            "GRANT EXECUTE ON FUNCTION "
            "public.app_accept_invitation(text, text, text) TO " + role
        )
        op.execute(
            "GRANT EXECUTE ON FUNCTION public.app_deactivate_member(uuid) TO " + role
        )
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE ON organization_invitations TO {role}"
        )
        op.execute(f"REVOKE DELETE ON organization_invitations FROM {role}")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS public.app_read_invitation(text)")
    op.execute("DROP FUNCTION IF EXISTS public.app_deactivate_member(uuid)")
    op.execute("DROP FUNCTION IF EXISTS public.app_accept_invitation(text, text, text)")

    role = _application_role()
    if role:
        op.execute(
            f"REVOKE SELECT, INSERT, UPDATE ON organization_invitations FROM {role}"
        )

    op.execute(
        "DROP POLICY IF EXISTS organization_invitations_update_admin "
        "ON organization_invitations"
    )
    op.execute(
        "DROP POLICY IF EXISTS organization_invitations_insert_admin "
        "ON organization_invitations"
    )
    op.execute(
        "DROP POLICY IF EXISTS organization_invitations_read_tenant_or_auditor "
        "ON organization_invitations"
    )
    op.execute("ALTER TABLE organization_invitations DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "uq_organization_invitations_pending_email",
        table_name="organization_invitations",
    )
    op.drop_index(
        "ix_organization_invitations_token_hash",
        table_name="organization_invitations",
    )
    op.drop_index(
        "ix_organization_invitations_organization_created",
        table_name="organization_invitations",
    )
    op.drop_table("organization_invitations")
