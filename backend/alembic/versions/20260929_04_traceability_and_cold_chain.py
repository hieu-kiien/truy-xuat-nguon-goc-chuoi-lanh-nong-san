"""Add traceability, custody, cold-chain records and tenant RLS.

Revision ID: 20260929_04
Revises: 20260929_03
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260929_04"
down_revision: str | None = "20260929_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_farms_id_organization", "farms", ["id", "organization_id"]
    )

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("min_temperature_c", sa.Numeric(8, 3)),
        sa.Column("max_temperature_c", sa.Numeric(8, 3)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "min_temperature_c IS NULL OR max_temperature_c IS NULL OR "
            "min_temperature_c <= max_temperature_c",
            name="ck_products_temperature_range",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_products_id_organization"),
    )
    op.create_index("ix_products_organization_created", "products", ["organization_id", "created_at"])

    op.create_table(
        "lots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_code", sa.String(80), nullable=False),
        sa.Column("lot_number", sa.String(80)),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("origin_organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("origin_farm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit", sa.String(24), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("harvested_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_lots_quantity_positive"),
        sa.CheckConstraint(
            "status IN ('created', 'harvested', 'processed', 'packed', 'in_transit', "
            "'received', 'stored', 'sold', 'discarded')",
            name="ck_lots_status",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["origin_organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["product_id", "origin_organization_id"], ["products.id", "products.organization_id"],
            ondelete="RESTRICT", name="fk_lots_product_origin_organization",
        ),
        sa.ForeignKeyConstraint(
            ["origin_farm_id", "origin_organization_id"], ["farms.id", "farms.organization_id"],
            ondelete="RESTRICT", name="fk_lots_farm_origin_organization",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_code", name="uq_lots_public_code"),
        sa.UniqueConstraint("origin_organization_id", "lot_number", name="uq_lots_origin_lot_number"),
    )
    op.create_index("ix_lots_organization_created", "lots", ["organization_id", "created_at", "id"])
    op.create_index("ix_lots_organization_status", "lots", ["organization_id", "status", "created_at"])

    op.create_table(
        "lot_lineage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_lot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_lot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation_type", sa.String(12), nullable=False),
        sa.Column("source_quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("source_lot_id <> target_lot_id", name="ck_lot_lineage_no_self"),
        sa.CheckConstraint("relation_type IN ('split', 'merge')", name="ck_lot_lineage_type"),
        sa.CheckConstraint("source_quantity > 0", name="ck_lot_lineage_quantity_positive"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_lot_id", "target_lot_id", name="uq_lot_lineage_pair"),
    )
    op.create_index("ix_lot_lineage_source", "lot_lineage", ["source_lot_id"])
    op.create_index("ix_lot_lineage_target", "lot_lineage", ["target_lot_id"])

    op.create_table(
        "lot_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_note", sa.String(500)),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('lot_created', 'harvested', 'processed', 'packed', 'stored', "
            "'inspection', 'shipped', 'received', 'sold', 'discarded', 'temperature_excursion')",
            name="ck_lot_events_type",
        ),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lot_events_lot_time", "lot_events", ["lot_id", "occurred_at", "id"])
    op.create_index("ix_lot_events_organization_time", "lot_events", ["organization_id", "occurred_at"])

    op.create_table(
        "shipments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receiver_organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("temperature_min_c", sa.Numeric(8, 3)),
        sa.Column("temperature_max_c", sa.Numeric(8, 3)),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("received_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("sender_organization_id <> receiver_organization_id", name="ck_shipments_distinct_parties"),
        sa.CheckConstraint("status IN ('in_transit', 'received', 'cancelled')", name="ck_shipments_status"),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sender_organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["receiver_organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["received_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shipments_sender_status", "shipments", ["sender_organization_id", "status"])
    op.create_index("ix_shipments_receiver_status", "shipments", ["receiver_organization_id", "status"])
    op.create_index(
        "uq_shipments_one_in_transit_per_lot", "shipments", ["lot_id"], unique=True,
        postgresql_where=sa.text("status = 'in_transit'"),
    )

    op.create_table(
        "sensors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_code", sa.String(80), nullable=False),
        sa.Column("label", sa.String(120)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "device_code", name="uq_sensor_org_device"),
        sa.UniqueConstraint("id", "organization_id", name="uq_sensors_id_organization"),
    )
    op.create_index("ix_sensors_organization_id", "sensors", ["organization_id"])

    op.create_table(
        "temperature_readings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sensor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_reading_id", sa.String(120), nullable=False),
        sa.Column("temperature_c", sa.Numeric(8, 3), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("temperature_c BETWEEN -100 AND 150", name="ck_temperature_reading_range"),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sensor_id", "organization_id"], ["sensors.id", "sensors.organization_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sensor_id", "source_reading_id", name="uq_reading_source"),
        sa.UniqueConstraint("id", "organization_id", name="uq_readings_id_organization"),
    )
    op.create_index("ix_temperature_readings_shipment_time", "temperature_readings", ["shipment_id", "measured_at"])
    op.create_index("ix_temperature_readings_organization_time", "temperature_readings", ["organization_id", "measured_at"])

    op.create_table(
        "cold_chain_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sensor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reading_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("temperature_c", sa.Numeric(8, 3), nullable=False),
        sa.Column("min_temperature_c", sa.Numeric(8, 3)),
        sa.Column("max_temperature_c", sa.Numeric(8, 3)),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by_id", postgresql.UUID(as_uuid=True)),
        sa.CheckConstraint("status IN ('open', 'resolved')", name="ck_cold_chain_alerts_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sensor_id"], ["sensors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reading_id", "organization_id"], ["temperature_readings.id", "temperature_readings.organization_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reading_id", name="uq_cold_chain_alert_reading"),
    )
    op.create_index("ix_cold_chain_alerts_organization_status", "cold_chain_alerts", ["organization_id", "status", "created_at"])

    # Event and lineage records are append-only at the DB role boundary.
    op.execute("REVOKE UPDATE, DELETE ON lot_events, lot_lineage FROM ttcs_app")

    # Identity tables are available only for the active login/session context.
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sessions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sessions FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY farms_organization_isolation ON farms")
    op.execute("ALTER TABLE farms ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE farms FORCE ROW LEVEL SECURITY")

    for table in (
        "products", "lots", "lot_lineage", "lot_events", "shipments",
        "sensors", "temperature_readings", "cold_chain_alerts",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY users_context_read ON users FOR SELECT
        USING (
            organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
            OR id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
            OR email = NULLIF(current_setting('app.login_email', true), '')
            OR id IN (
                SELECT s.user_id FROM sessions s
                WHERE s.token_hash = NULLIF(current_setting('app.session_token_hash', true), '')
            )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY users_context_insert ON users FOR INSERT
        WITH CHECK (
            organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
            OR organization_id = NULLIF(current_setting('app.provisioning_organization', true), '')::uuid
        )
        """
    )
    op.execute(
        """
        CREATE POLICY users_context_update ON users FOR UPDATE
        USING (
            organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
            OR email = NULLIF(current_setting('app.login_email', true), '')
            OR id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        WITH CHECK (
            organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
            OR email = NULLIF(current_setting('app.login_email', true), '')
        )
        """
    )
    op.execute(
        """
        CREATE POLICY sessions_context_select ON sessions FOR SELECT
        USING (
            token_hash = NULLIF(current_setting('app.session_token_hash', true), '')
            OR user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        """
    )
    op.execute(
        """
        CREATE POLICY sessions_context_insert ON sessions FOR INSERT
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY sessions_context_update ON sessions FOR UPDATE
        USING (
            token_hash = NULLIF(current_setting('app.session_token_hash', true), '')
            OR user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )

    op.execute(
        """
        CREATE POLICY farms_tenant_read ON farms FOR SELECT
        USING (
            organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
            OR current_setting('app.current_role', true) = 'inspector'
            OR EXISTS (
                SELECT 1 FROM lots l
                WHERE l.origin_farm_id = farms.id
                  AND l.public_code = NULLIF(current_setting('app.public_trace_code', true), '')
            )
            OR EXISTS (
                SELECT 1 FROM lots l
                WHERE l.origin_farm_id = farms.id
                  AND l.organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
            )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY farms_tenant_write ON farms FOR ALL
        USING (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)
        WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)
        """
    )

    op.execute(
        """
        CREATE POLICY products_tenant_read ON products FOR SELECT
        USING (
            organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
            OR current_setting('app.current_role', true) = 'inspector'
            OR EXISTS (
                SELECT 1 FROM lots l
                WHERE l.product_id = products.id AND (
                    l.public_code = NULLIF(current_setting('app.public_trace_code', true), '')
                    OR l.organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
                )
            )
        )
        """
    )
    op.execute("CREATE POLICY products_tenant_write ON products FOR ALL USING (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid) WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)")

    op.execute(
        """
        CREATE POLICY lots_tenant_read ON lots FOR SELECT
        USING (
            organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
            OR current_setting('app.current_role', true) = 'inspector'
            OR public_code = NULLIF(current_setting('app.public_trace_code', true), '')
            OR EXISTS (
                SELECT 1 FROM shipments s WHERE s.lot_id = lots.id
                  AND s.receiver_organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
                  AND s.status = 'in_transit'
            )
        )
        """
    )
    op.execute("CREATE POLICY lots_tenant_write ON lots FOR ALL USING (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid) WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)")
    op.execute("CREATE POLICY lots_receiver_update ON lots FOR UPDATE USING (EXISTS (SELECT 1 FROM shipments s WHERE s.lot_id = lots.id AND s.receiver_organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid AND s.status = 'in_transit')) WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)")

    op.execute(
        """
        CREATE POLICY lineage_context_read ON lot_lineage FOR SELECT
        USING (
            current_setting('app.current_role', true) = 'inspector'
            OR EXISTS (
                SELECT 1 FROM lots l WHERE l.id IN (lot_lineage.source_lot_id, lot_lineage.target_lot_id)
                  AND l.organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
            )
            OR EXISTS (
                SELECT 1 FROM lots l WHERE l.id IN (lot_lineage.source_lot_id, lot_lineage.target_lot_id)
                  AND l.public_code = NULLIF(current_setting('app.public_trace_code', true), '')
            )
        )
        """
    )
    op.execute("CREATE POLICY lineage_tenant_insert ON lot_lineage FOR INSERT WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)")
    op.execute(
        """
        CREATE POLICY events_context_read ON lot_events FOR SELECT
        USING (
            organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
            OR current_setting('app.current_role', true) = 'inspector'
            OR EXISTS (
                SELECT 1 FROM lots l WHERE l.id = lot_events.lot_id
                  AND l.organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
            )
            OR EXISTS (
                SELECT 1 FROM lots l WHERE l.id = lot_events.lot_id
                  AND l.public_code = NULLIF(current_setting('app.public_trace_code', true), '')
            )
        )
        """
    )
    op.execute("CREATE POLICY events_tenant_insert ON lot_events FOR INSERT WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)")

    op.execute(
        """
        CREATE POLICY shipments_party_read ON shipments FOR SELECT
        USING (
            organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
            OR sender_organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
            OR receiver_organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid
            OR current_setting('app.current_role', true) = 'inspector'
        )
        """
    )
    op.execute("CREATE POLICY shipments_sender_insert ON shipments FOR INSERT WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid AND sender_organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)")
    op.execute("CREATE POLICY shipments_party_update ON shipments FOR UPDATE USING (sender_organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid OR receiver_organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid) WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid OR organization_id = sender_organization_id OR organization_id = receiver_organization_id)")

    op.execute("CREATE POLICY sensors_tenant_all ON sensors FOR ALL USING (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid OR current_setting('app.current_role', true) = 'inspector') WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)")
    op.execute("CREATE POLICY readings_tenant_read ON temperature_readings FOR SELECT USING (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid OR current_setting('app.current_role', true) = 'inspector' OR EXISTS (SELECT 1 FROM shipments s WHERE s.id = temperature_readings.shipment_id AND (s.sender_organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid OR s.receiver_organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)))")
    op.execute("CREATE POLICY readings_tenant_insert ON temperature_readings FOR INSERT WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)")
    op.execute("CREATE POLICY alerts_tenant_read ON cold_chain_alerts FOR SELECT USING (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid OR current_setting('app.current_role', true) = 'inspector')")
    op.execute("CREATE POLICY alerts_tenant_insert ON cold_chain_alerts FOR INSERT WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)")
    op.execute("CREATE POLICY alerts_tenant_update ON cold_chain_alerts FOR UPDATE USING (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid) WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)")

    # Shipment reception needs these specific columns; unrestricted DELETE remains revoked.
    op.execute("REVOKE DELETE ON shipments, products, lots, lot_lineage, lot_events, sensors, temperature_readings, cold_chain_alerts FROM ttcs_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON products TO ttcs_app")
    op.execute("GRANT SELECT, INSERT ON lots, shipments, sensors, cold_chain_alerts TO ttcs_app")
    op.execute("GRANT SELECT, INSERT ON lot_lineage, lot_events, temperature_readings TO ttcs_app")
    op.execute("GRANT UPDATE (status, organization_id) ON lots TO ttcs_app")
    op.execute("GRANT UPDATE (status, received_at, received_by_id, organization_id, temperature_min_c, temperature_max_c) ON shipments TO ttcs_app")
    op.execute("GRANT UPDATE (is_active) ON sensors TO ttcs_app")
    op.execute("GRANT UPDATE (status, resolved_at, resolved_by_id) ON cold_chain_alerts TO ttcs_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON users TO ttcs_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON sessions TO ttcs_app")


def downgrade() -> None:
    for table in (
        "cold_chain_alerts", "temperature_readings", "sensors", "shipments",
        "lot_events", "lot_lineage", "lots", "products",
    ):
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.drop_table(table)

    op.execute("DROP POLICY IF EXISTS users_context_read ON users")
    op.execute("DROP POLICY IF EXISTS users_context_insert ON users")
    op.execute("DROP POLICY IF EXISTS users_context_update ON users")
    op.execute("DROP POLICY IF EXISTS sessions_context_select ON sessions")
    op.execute("DROP POLICY IF EXISTS sessions_context_insert ON sessions")
    op.execute("DROP POLICY IF EXISTS sessions_context_update ON sessions")
    op.execute("ALTER TABLE users NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sessions NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sessions DISABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY farms_organization_isolation ON farms USING (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid) WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)")
    op.drop_constraint("uq_farms_id_organization", "farms", type_="unique")
