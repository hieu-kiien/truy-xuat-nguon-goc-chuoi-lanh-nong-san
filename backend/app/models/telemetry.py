"""Models for cold chain telemetry temperature readings (N3-60, S-41)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TemperatureReading(Base):
    """An immutable time-series temperature reading recorded by a refrigerated container sensor."""

    __tablename__ = "temperature_readings"
    __table_args__ = (
        UniqueConstraint("shipment_id", "recorded_at", name="uq_shipment_reading_time"),
        Index("ix_temperature_readings_shipment_id", "shipment_id"),
        Index("ix_temperature_readings_container_code", "container_code"),
        Index("ix_temperature_readings_recorded_at", "recorded_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    shipment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "shipments.id",
            name="fk_temperature_readings_shipment_id_shipments",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    container_code: Mapped[str] = mapped_column(String(64), nullable=False)
    temperature_celsius: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # Relationships
    shipment = relationship("Shipment", foreign_keys=[shipment_id])
