"""Add privacy requests and allow an anonymized farm to drop its coordinates (N3-75).

Revision ID: 20261021_43
Revises: 20261021_42
Create Date: 2026-10-21 03:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "20261021_43"
down_revision: str | Sequence[str] | None = "20261021_42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _application_role() -> str | None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text(
            "SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :role AND :role <> current_user"
        ),
        {"role": settings.DB_USER},
    ).scalar()
    if not exists:
        return None
    return bind.dialect.identifier_preparer.quote(settings.DB_USER)


def upgrade() -> None:
    # 1. Trail of the privacy requests. It never stores the identity itself.
    op.create_table(
        "pii_anonymization_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'requested'"),
            nullable=False,
        ),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_pii_requests_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.id"],
            name="fk_pii_requests_farm_id_farms",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"],
            ["users.id"],
            name="fk_pii_requests_requested_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_user_id"],
            ["users.id"],
            name="fk_pii_requests_decided_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pii_requests_org_requested",
        "pii_anonymization_requests",
        ["organization_id", "requested_at"],
    )

    # 2. Only the organization that asked may read its own requests; the
    #    system admin reads all of them to carry the request out.
    op.execute("ALTER TABLE pii_anonymization_requests ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY pii_requests_read_tenant_or_admin ON pii_anonymization_requests
        FOR SELECT
        USING (
            organization_id = public.app_current_organization_id()
            OR public.app_current_role() = 'system_admin'
        )
        """
    )
    op.execute(
        """
        CREATE POLICY pii_requests_insert_tenant ON pii_anonymization_requests
        FOR INSERT
        WITH CHECK (
            organization_id = public.app_current_organization_id()
            AND requested_by_user_id = public.app_current_user_id()
        )
        """
    )
    op.execute(
        """
        CREATE POLICY pii_requests_update_admin ON pii_anonymization_requests
        FOR UPDATE
        USING (public.app_current_role() = 'system_admin')
        WITH CHECK (public.app_current_role() = 'system_admin')
        """
    )

    role = _application_role()
    if role:
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE ON pii_anonymization_requests TO {role}"
        )
        op.execute(f"REVOKE DELETE ON pii_anonymization_requests FROM {role}")

    # 3. A farm that no longer holds a precise location keeps its history but
    #    drops the coordinates that identified it.
    op.alter_column("farms", "latitude", existing_type=sa.Numeric(9, 6), nullable=True)
    op.alter_column("farms", "longitude", existing_type=sa.Numeric(9, 6), nullable=True)

    # 4. The erase itself. It has to reach rows of another organization, which
    #    the runtime role may not do directly, so the operation is a single
    #    bounded SECURITY DEFINER function like the overdue handover marker.
    #    The event log is never touched.
    op.execute("""CREATE FUNCTION public.app_anonymize_organization(
    target_organization uuid, target_farm uuid)
    RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog, public AS $$
    BEGIN
      IF public.app_current_role() <> 'system_admin' THEN
        RAISE EXCEPTION 'Only a system administrator may erase identifying data';
      END IF;
      IF target_organization IS NULL OR target_farm IS NULL THEN
        RAISE EXCEPTION 'Missing organization or farm';
      END IF;
      UPDATE public.users u SET
        full_name = 'Nông hộ ẩn danh #' || upper(substr(replace(u.id::text, '-', ''), 1, 8)),
        email = 'anonymized+' || replace(u.id::text, '-', '') || '@anonymized.invalid'
      WHERE u.organization_id = target_organization;
      UPDATE public.organizations o SET
        name = 'Tổ chức ẩn danh #' || upper(substr(replace(o.id::text, '-', ''), 1, 8))
      WHERE o.id = target_organization;
      UPDATE public.farms f SET
        name = 'Vùng trồng ẩn danh #' || upper(substr(replace(f.id::text, '-', ''), 1, 8)),
        latitude = NULL,
        longitude = NULL
      WHERE f.id = target_farm AND f.organization_id = target_organization;
    END; $$""")
    op.execute(
        "REVOKE ALL ON FUNCTION public.app_anonymize_organization(uuid, uuid) FROM PUBLIC"
    )
    if role:
        op.execute(
            f"GRANT EXECUTE ON FUNCTION public.app_anonymize_organization(uuid, uuid) TO {role}"
        )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS public.app_anonymize_organization(uuid, uuid)")

    op.alter_column(
        "farms", "longitude", existing_type=sa.Numeric(9, 6), nullable=False
    )
    op.alter_column("farms", "latitude", existing_type=sa.Numeric(9, 6), nullable=False)

    role = _application_role()
    if role:
        op.execute(f"REVOKE ALL ON pii_anonymization_requests FROM {role}")

    op.execute(
        "DROP POLICY IF EXISTS pii_requests_update_admin ON pii_anonymization_requests"
    )
    op.execute(
        "DROP POLICY IF EXISTS pii_requests_insert_tenant ON pii_anonymization_requests"
    )
    op.execute(
        "DROP POLICY IF EXISTS pii_requests_read_tenant_or_admin ON pii_anonymization_requests"
    )
    op.execute("ALTER TABLE pii_anonymization_requests DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_pii_requests_org_requested", table_name="pii_anonymization_requests"
    )
    op.drop_table("pii_anonymization_requests")
