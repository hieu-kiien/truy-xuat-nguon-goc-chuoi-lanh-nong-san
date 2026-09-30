"""Harden tenant isolation, least privilege, and referential integrity.

Revision ID: 20260929_05
Revises: 20260929_04
Create Date: 2026-09-30

Scope: N3-6 (tenant isolation / authorization) and N3-7 (farm relations).

Changes
-------
1. Apply the database-level CONNECT lockdown to the database actually being
   migrated instead of the hard-coded ``ttcs_db`` name, so the same migration
   chain is safe to apply to any environment (CI, staging, preview).
2. Backfill ``lot_events.organization_id`` from the lot's owning organization
   and enforce it with a composite foreign key. Custody transfers used to
   re-home an event onto the receiving organization, which split one lot's
   append-only provenance history across two tenants.
3. Add composite foreign keys on ``lot_lineage`` so a lineage edge cannot
   reference lots outside the edge's own organization.
4. Replace the ``FOR ALL`` sensor policy, which granted inspectors write
   access through its ``USING`` clause, with separate read and write policies.
5. Remove the blanket inspector read on ``farms``. Inspectors hold no
   ``farms:read`` permission, so this clause only widened exposure.
6. Add ``ck_users_failed_attempts`` plus server defaults so login counters and
   activation flags are constrained by the database, not only by the ORM.
"""

from collections.abc import Sequence

from alembic import op

from app.core.db_identity import application_database_role

revision: str = "20260929_05"
down_revision: str | None = "20260929_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CURRENT_ORGANIZATION = "NULLIF(current_setting('app.current_organization', true), '')::uuid"


def upgrade() -> None:
    app_role = application_database_role()

    # 1. Lock down CONNECT against the database this migration is applied to.
    op.execute(
        "DO $$ BEGIN EXECUTE format("
        "'REVOKE CONNECT ON DATABASE %I FROM PUBLIC', current_database());"
        "EXECUTE format('GRANT CONNECT ON DATABASE %I TO %I', "
        "current_database(), "
        f"'{app_role}'); END $$;"
    )
    op.execute(f"REVOKE CREATE ON SCHEMA public FROM PUBLIC, {app_role}")
    op.execute(f"REVOKE ALL ON DATABASE {op.get_bind().engine.url.database} FROM {app_role}")
    op.execute(
        f"GRANT CONNECT, TEMPORARY ON DATABASE {op.get_bind().engine.url.database} TO {app_role}"
    )

    # 6. Login counter / activation integrity at the database level.
    op.execute(
        "ALTER TABLE users ALTER COLUMN failed_login_attempts SET DEFAULT 0, "
        "ALTER COLUMN is_active SET DEFAULT true"
    )
    op.execute("ALTER TABLE organizations ALTER COLUMN is_active SET DEFAULT true")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT ck_users_failed_attempts "
        "CHECK (failed_login_attempts >= 0)"
    )

    # 8. Enforce the email normalization the login endpoint relies on.
    #    Authentication always looks an account up with a case-folded address,
    #    so a row stored as `User@Example.com` would be unreachable and, because
    #    UNIQUE is case sensitive, could shadow a real account. Normalize the
    #    existing rows and then forbid non-normalized ones.
    op.execute("UPDATE users SET email = lower(email) WHERE email <> lower(email)")
    op.execute("ALTER TABLE users ADD CONSTRAINT ck_users_email_normalized CHECK (email = lower(email))")

    # 2. Repair and then enforce lot_events tenant integrity.
    op.execute(
        "UPDATE lot_events e SET organization_id = l.organization_id "
        "FROM lots l WHERE l.id = e.lot_id AND e.organization_id <> l.organization_id"
    )
    op.create_unique_constraint("uq_lots_id_organization", "lots", ["id", "organization_id"])
    op.create_foreign_key(
        "fk_lot_events_lot_organization",
        "lot_events",
        "lots",
        ["lot_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="RESTRICT",
    )

    # 3. A lineage edge must reference lots of its own organization.
    op.create_foreign_key(
        "fk_lot_lineage_source_organization",
        "lot_lineage",
        "lots",
        ["source_lot_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_lot_lineage_target_organization",
        "lot_lineage",
        "lots",
        ["target_lot_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="RESTRICT",
    )

    # 7. Reconcile cold-chain foreign keys with the SQLAlchemy models. The
    #    models already declared these constraints but revision 20260929_04
    #    never created them, so `alembic check` reported drift. Creating them
    #    also stops a reading or alert from being attributed to an organization
    #    that does not own the underlying sensor or reading.
    op.create_foreign_key(
        "fk_temperature_readings_organization_id",
        "temperature_readings",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_cold_chain_alerts_reading_organization",
        "cold_chain_alerts",
        "temperature_readings",
        ["reading_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="RESTRICT",
    )

    # 9. Restore the mandated 403 for cross-tenant access.
    #
    #    `get_tenant_record` distinguishes "forbidden" from "not found" by
    #    re-querying the record without a tenant filter. Row-level security
    #    makes that probe blind: the row belongs to another organization, so
    #    the policy hides it and the endpoint answered 404 instead of the 403
    #    the acceptance criteria require. This SECURITY DEFINER helper performs
    #    the existence check as the table owner (row_security = off).
    #
    #    It is deliberately minimal and non-leaky: it accepts a table name only
    #    from a fixed allowlist (so there is no dynamic-SQL injection surface)
    #    and returns a single boolean, never row data. Execution is revoked from
    #    PUBLIC and granted solely to the application role.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_tenant_record_exists(p_table text, p_id uuid)
        RETURNS boolean
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        SET row_security = off
        AS $$
        DECLARE
            found boolean;
        BEGIN
            IF p_table NOT IN (
                'farms', 'products', 'lots', 'shipments', 'sensors',
                'temperature_readings', 'cold_chain_alerts', 'lot_lineage',
                'lot_events'
            ) THEN
                RETURN false;
            END IF;
            EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I WHERE id = $1)', p_table)
                INTO found USING p_id;
            RETURN found;
        END;
        $$
        """
    )
    op.execute("REVOKE ALL ON FUNCTION app_tenant_record_exists(text, uuid) FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION app_tenant_record_exists(text, uuid) TO {app_role}")

    # 4. Inspection is read-only: the `FOR ALL` policy allowed inspectors to
    #    satisfy the USING clause for UPDATE/DELETE, and WITH CHECK was the only
    #    thing stopping a cross-tenant write. Split read from write.
    op.execute("DROP POLICY IF EXISTS sensors_tenant_all ON sensors")
    op.execute(
        f"CREATE POLICY sensors_tenant_read ON sensors FOR SELECT USING ("
        f"organization_id = {CURRENT_ORGANIZATION} "
        "OR current_setting('app.current_role', true) = 'inspector')"
    )
    op.execute(
        f"CREATE POLICY sensors_tenant_insert ON sensors FOR INSERT WITH CHECK ("
        f"organization_id = {CURRENT_ORGANIZATION})"
    )
    op.execute(
        f"CREATE POLICY sensors_tenant_update ON sensors FOR UPDATE USING ("
        f"organization_id = {CURRENT_ORGANIZATION}) WITH CHECK ("
        f"organization_id = {CURRENT_ORGANIZATION})"
    )

    # 5. Inspectors have no farms:read permission, so the blanket inspector
    #    clause on farms only widened the blast radius of a role mistake.
    op.execute("DROP POLICY IF EXISTS farms_tenant_read ON farms")
    op.execute(
        """
        CREATE POLICY farms_tenant_read ON farms FOR SELECT
        USING (
            organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
            OR EXISTS (
                SELECT 1 FROM lots l
                WHERE l.origin_farm_id = farms.id
                  AND (l.public_code = NULLIF(current_setting('app.public_trace_code', true), '')
                       OR l.id::text = ANY(string_to_array(NULLIF(current_setting('app.public_trace_lot_ids', true), ''), ',')))
            )
            OR EXISTS (
                SELECT 1 FROM lots l
                WHERE l.origin_farm_id = farms.id
                  AND l.organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
            )
        )
        """
    )


def downgrade() -> None:
    app_role = application_database_role()

    op.execute("DROP FUNCTION IF EXISTS app_tenant_record_exists(text, uuid)")

    op.execute("DROP POLICY IF EXISTS farms_tenant_read ON farms")
    op.execute(
        f"CREATE POLICY farms_tenant_read ON farms FOR SELECT USING ("
        f"organization_id = {CURRENT_ORGANIZATION} "
        "OR current_setting('app.current_role', true) = 'inspector')"
    )

    op.execute("DROP POLICY IF EXISTS sensors_tenant_read ON sensors")
    op.execute("DROP POLICY IF EXISTS sensors_tenant_insert ON sensors")
    op.execute("DROP POLICY IF EXISTS sensors_tenant_update ON sensors")
    op.execute(
        f"CREATE POLICY sensors_tenant_all ON sensors FOR ALL USING ("
        f"organization_id = {CURRENT_ORGANIZATION} "
        "OR current_setting('app.current_role', true) = 'inspector') WITH CHECK ("
        f"organization_id = {CURRENT_ORGANIZATION})"
    )

    op.drop_constraint(
        "fk_cold_chain_alerts_reading_organization", "cold_chain_alerts", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_temperature_readings_organization_id", "temperature_readings", type_="foreignkey"
    )

    op.drop_constraint(
        "fk_lot_lineage_target_organization", "lot_lineage", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_lot_lineage_source_organization", "lot_lineage", type_="foreignkey"
    )
    op.drop_constraint("fk_lot_events_lot_organization", "lot_events", type_="foreignkey")
    op.drop_constraint("uq_lots_id_organization", "lots", type_="unique")
    op.drop_constraint("ck_users_failed_attempts", "users", type_="check")
    op.drop_constraint("ck_users_email_normalized", "users", type_="check")

    database = op.get_bind().engine.url.database
    op.execute(f"GRANT ALL ON DATABASE {database} TO {app_role}")
