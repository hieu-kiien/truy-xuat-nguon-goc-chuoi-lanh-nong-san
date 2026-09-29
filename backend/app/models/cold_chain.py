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
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Shipment(Base):
    __tablename__ = "shipments"
    __table_args__ = (
        CheckConstraint(
            "sender_organization_id <> receiver_organization_id",
            name="ck_shipments_distinct_parties",
        ),
        CheckConstraint(
            "status IN ('in_transit', 'received', 'cancelled')",
            name="ck_shipments_status",
        ),
        Index("ix_shipments_sender_status", "sender_organization_id", "status"),
        Index("ix_shipments_receiver_status", "receiver_organization_id", "status"),
        Index(
            "uq_shipments_one_in_transit_per_lot",
            "lot_id",
            unique=True,
            postgresql_where=text("status = 'in_transit'"),
        ),
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
    sender_organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    receiver_organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="in_transit")
    shipped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    temperature_min_c: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    temperature_max_c: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    created_by_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    received_by_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Sensor(Base):
    __tablename__ = "sensors"
    __table_args__ = (
        UniqueConstraint("organization_id", "device_code", name="uq_sensor_org_device"),
        UniqueConstraint("id", "organization_id", name="uq_sensors_id_organization"),
        Index("ix_sensors_organization_id", "organization_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    shipment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("shipments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    device_code: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TemperatureReading(Base):
    __tablename__ = "temperature_readings"
    __table_args__ = (
        UniqueConstraint("sensor_id", "source_reading_id", name="uq_reading_source"),
        UniqueConstraint("id", "organization_id", name="uq_readings_id_organization"),
        CheckConstraint(
            "temperature_c BETWEEN -100 AND 150",
            name="ck_temperature_reading_range",
        ),
        Index("ix_temperature_readings_shipment_time", "shipment_id", "measured_at"),
        Index("ix_temperature_readings_organization_time", "organization_id", "measured_at"),
        ForeignKeyConstraint(
            ["sensor_id", "organization_id"],
            ["sensors.id", "sensors.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    shipment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("shipments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sensor_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    source_reading_id: Mapped[str] = mapped_column(String(120), nullable=False)
    temperature_c: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ColdChainAlert(Base):
    __tablename__ = "cold_chain_alerts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'resolved')", name="ck_cold_chain_alerts_status"
        ),
        Index(
            "ix_cold_chain_alerts_organization_status",
            "organization_id",
            "status",
            "created_at",
        ),
        ForeignKeyConstraint(
            ["reading_id", "organization_id"],
            ["temperature_readings.id", "temperature_readings.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    shipment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("shipments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sensor_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("sensors.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reading_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False, unique=True
    )
    temperature_c: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    min_temperature_c: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    max_temperature_c: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
