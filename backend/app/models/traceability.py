from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Lot(Base):
    __tablename__ = "lots"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_lots_quantity_positive"),
        CheckConstraint(
            "status IN ('created', 'harvested', 'processed', 'packed', 'in_transit', "
            "'received', 'stored', 'sold', 'discarded')",
            name="ck_lots_status",
        ),
        ForeignKeyConstraint(
            ["product_id", "origin_organization_id"],
            ["products.id", "products.organization_id"],
            ondelete="RESTRICT",
            name="fk_lots_product_origin_organization",
        ),
        ForeignKeyConstraint(
            ["origin_farm_id", "origin_organization_id"],
            ["farms.id", "farms.organization_id"],
            ondelete="RESTRICT",
            name="fk_lots_farm_origin_organization",
        ),
        UniqueConstraint("id", "organization_id", name="uq_lots_id_organization"),
        UniqueConstraint(
            "origin_organization_id", "lot_number", name="uq_lots_origin_lot_number"
        ),
        UniqueConstraint("public_code", name="uq_lots_public_code"),
        Index("ix_lots_organization_created", "organization_id", "created_at", "id"),
        Index("ix_lots_organization_status", "organization_id", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    public_code: Mapped[str] = mapped_column(String(80), nullable=False)
    lot_number: Mapped[str | None] = mapped_column(String(80))
    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    origin_organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    origin_farm_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="created")
    harvested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LotLineage(Base):
    __tablename__ = "lot_lineage"
    __table_args__ = (
        UniqueConstraint("source_lot_id", "target_lot_id", name="uq_lot_lineage_pair"),
        CheckConstraint(
            "source_lot_id <> target_lot_id", name="ck_lot_lineage_no_self"
        ),
        CheckConstraint(
            "relation_type IN ('split', 'merge')", name="ck_lot_lineage_type"
        ),
        CheckConstraint("source_quantity > 0", name="ck_lot_lineage_quantity_positive"),
        # A lineage edge may only reference lots owned by the same organization
        # as the edge itself, so provenance cannot be forged across tenants even
        # by a client holding the application database role.
        ForeignKeyConstraint(
            ["source_lot_id", "organization_id"],
            ["lots.id", "lots.organization_id"],
            ondelete="RESTRICT",
            name="fk_lot_lineage_source_organization",
        ),
        ForeignKeyConstraint(
            ["target_lot_id", "organization_id"],
            ["lots.id", "lots.organization_id"],
            ondelete="RESTRICT",
            name="fk_lot_lineage_target_organization",
        ),
        Index("ix_lot_lineage_source", "source_lot_id"),
        Index("ix_lot_lineage_target", "target_lot_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_lot_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("lots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_lot_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("lots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    relation_type: Mapped[str] = mapped_column(String(12), nullable=False)
    source_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LotEvent(Base):
    __tablename__ = "lot_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('lot_created', 'harvested', 'processed', 'packed', "
            "'stored', 'inspection', 'shipped', 'received', 'sold', 'discarded', "
            "'temperature_excursion')",
            name="ck_lot_events_type",
        ),
        # The event is always recorded against the organization that currently
        # custodies the lot, so one lot's history never splits across tenants.
        ForeignKeyConstraint(
            ["lot_id", "organization_id"],
            ["lots.id", "lots.organization_id"],
            ondelete="RESTRICT",
            name="fk_lot_events_lot_organization",
        ),
        Index("ix_lot_events_lot_time", "lot_id", "occurred_at", "id"),
        Index("ix_lot_events_organization_time", "organization_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    lot_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("lots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    public_note: Mapped[str | None] = mapped_column(String(500))
    details: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
