"""Hourly aggregates of old temperature readings (N3-64, S-51).

One row per hour, holding the minimum, the maximum and the average of the
readings of that hour. ``reading_count = 0`` marks an hour without any
reading, so a gap in the series stays visible.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TemperatureHourlyAggregate(Base):
    """One hour of an old temperature series, summarised (N3-64)."""

    __tablename__ = "temperature_hourly_aggregates"
    __table_args__ = (
        CheckConstraint(
            "reading_count >= 0", name="ck_temperature_hourly_aggregates_count"
        ),
        CheckConstraint(
            "(reading_count = 0 AND min_temperature_celsius IS NULL "
            "AND max_temperature_celsius IS NULL "
            "AND avg_temperature_celsius IS NULL) "
            "OR (reading_count > 0 AND min_temperature_celsius IS NOT NULL "
            "AND max_temperature_celsius IS NOT NULL "
            "AND avg_temperature_celsius IS NOT NULL)",
            name="ck_temperature_hourly_aggregates_gap_marker",
        ),
        UniqueConstraint(
            "shipment_id",
            "bucket_start",
            name="uq_temperature_hourly_aggregates_shipment_bucket",
        ),
        Index(
            "ix_temperature_hourly_aggregates_shipment_bucket",
            "shipment_id",
            "bucket_start",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    shipment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("shipments.id", ondelete="CASCADE"),
        nullable=False,
    )
    container_code: Mapped[str] = mapped_column(String(64), nullable=False)
    bucket_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reading_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    min_temperature_celsius: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    max_temperature_celsius: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    avg_temperature_celsius: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("now()"),
    )
