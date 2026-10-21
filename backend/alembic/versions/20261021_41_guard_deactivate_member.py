"""Guard the deactivation of a member so an organization cannot lock itself out.

An organization administrator could deactivate the last active administrator
of their organization, or deactivate their own account. In both cases nobody
would be left who can invite members or manage the organization any more.

Revision ID: 20261021_41
Revises: 20261021_40
Create Date: 2026-10-21 19:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261021_41"
down_revision: str | Sequence[str] | None = "20261021_40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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
            target_role text;
            caller_org uuid;
            caller_role text;
            active_admins integer;
        BEGIN
            caller_org := public.app_current_organization_id();
            caller_role := public.app_current_role();

            IF caller_role NOT IN ('organization_admin', 'system_admin') THEN
                RAISE EXCEPTION 'Only an organization administrator may deactivate a member'
                    USING ERRCODE = 'insufficient_privilege';
            END IF;

            SELECT organization_id, role_code
              INTO target_org, target_role
              FROM public.users WHERE id = p_user_id;

            IF target_org IS NULL THEN
                RAISE EXCEPTION 'Unknown member'
                    USING ERRCODE = 'no_data_found';
            END IF;

            IF target_org <> caller_org AND caller_role <> 'system_admin' THEN
                RAISE EXCEPTION 'The member belongs to another organization'
                    USING ERRCODE = 'insufficient_privilege';
            END IF;

            -- Nobody may switch off their own account from the member list.
            IF p_user_id = public.app_current_user_id() THEN
                RAISE EXCEPTION 'You cannot deactivate your own account'
                    USING ERRCODE = 'insufficient_privilege';
            END IF;

            -- An organization keeps at least one active administrator, so the
            -- organization can still invite members and manage its people.
            -- The guard applies to the system administrator as well, because
            -- there is no way to switch an account back on from the interface.
            IF target_role = 'organization_admin' THEN
                SELECT count(*) INTO active_admins
                  FROM public.users
                 WHERE organization_id = target_org
                   AND role_code = 'organization_admin'
                   AND is_active;

                IF active_admins <= 1 THEN
                    RAISE EXCEPTION 'The organization must keep at least one active administrator'
                        USING ERRCODE = 'insufficient_privilege';
                END IF;
            END IF;

            UPDATE public.users SET is_active = false WHERE id = p_user_id;
            RETURN true;
        END;
        $function$;
        """
    )


def downgrade() -> None:
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
