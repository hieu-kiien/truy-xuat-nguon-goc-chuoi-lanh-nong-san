"""Integration test suite for N3-64: hourly aggregates of old temperature data.

Readings older than the retention window are folded into one row per hour
holding the minimum, the maximum and the average. Hours without any reading
stay visible as a gap.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.jobs import telemetry_compactor
from app.models.farm import Farm
from app.models.lot import Lot
from app.models.product import Product
from app.models.shipment import Shipment
from app.models.telemetry import TemperatureReading
from app.models.telemetry_aggregate import TemperatureHourlyAggregate
from tests.conftest import IdentityFixture

NOW = datetime(2026, 10, 21, 3, 0, 0, tzinfo=UTC)


def _seed_shipment(
    db: Session, identity: IdentityFixture, *, completed: bool
) -> Shipment:
    farm = Farm(
        organization_id=identity.organization_id,
        name=f"compact-farm-{uuid4().hex[:8]}",
        area_ha=Decimal("1.0000"),
        latitude=Decimal("10.000000"),
        longitude=Decimal("106.000000"),
    )
    product = Product(name=f"compact-product-{uuid4().hex[:8]}", unit="kg")
    db.add_all([farm, product])
    db.flush()
    lot = Lot(
        organization_id=identity.organization_id,
        current_holder_organization_id=identity.organization_id,
        farm_id=farm.id,
        name="Lô vận chuyển",
        lot_code=uuid4().hex[:8].upper(),
        product_id=product.id,
        quantity=Decimal("10.000"),
        remaining_quantity=Decimal("10.000"),
        status="active",
    )
    db.add(lot)
    db.flush()
    shipment = Shipment(
        shipment_code=f"SH-{uuid4().hex[:8].upper()}",
        organization_id=identity.organization_id,
        created_by_user_id=identity.user_id,
        container_code=f"RF-{uuid4().hex[:6].upper()}",
        status="completed" if completed else "in_transit",
        created_at=NOW - timedelta(days=60),
        completed_at=NOW - timedelta(days=40) if completed else None,
    )
    db.add(shipment)
    db.commit()
    return shipment


def _add_reading(
    db: Session, shipment: Shipment, moment: datetime, temperature: str
) -> None:
    db.add(
        TemperatureReading(
            shipment_id=shipment.id,
            container_code=shipment.container_code,
            temperature_celsius=Decimal(temperature),
            recorded_at=moment,
        )
    )
    db.commit()


def test_n3_64_old_readings_are_folded_into_hourly_rows(
    admin_session: Session, identity_factory
):
    """Readings older than the window become one row per hour."""
    carrier = identity_factory(role="transporter", organization_type="transport")
    shipment = _seed_shipment(admin_session, carrier, completed=True)

    old = NOW - timedelta(days=45)
    _add_reading(admin_session, shipment, old, "4.00")
    _add_reading(admin_session, shipment, old + timedelta(minutes=10), "6.00")
    _add_reading(admin_session, shipment, old + timedelta(minutes=20), "2.00")
    _add_reading(admin_session, shipment, old + timedelta(hours=2), "5.00")
    # A recent reading stays raw.
    _add_reading(admin_session, shipment, NOW - timedelta(hours=2), "4.50")

    summary = telemetry_compactor.compact_old_readings(
        admin_session, retention_days=30, now=NOW
    )

    assert summary["compacted_readings"] == 4
    assert summary["aggregate_rows"] == 2
    assert summary["gap_rows"] == 1

    rows = list(
        admin_session.scalars(
            select(TemperatureHourlyAggregate)
            .where(TemperatureHourlyAggregate.shipment_id == shipment.id)
            .order_by(TemperatureHourlyAggregate.bucket_start.asc())
        ).all()
    )
    assert len(rows) == 3
    first = rows[0]
    assert first.reading_count == 3
    assert first.min_temperature_celsius == Decimal("2.00")
    assert first.max_temperature_celsius == Decimal("6.00")
    assert first.avg_temperature_celsius == Decimal("4.00")

    # The empty hour between the two busy hours stays visible as a gap.
    assert rows[1].reading_count == 0
    assert rows[1].min_temperature_celsius is None
    assert rows[1].avg_temperature_celsius is None

    assert rows[2].reading_count == 1
    assert rows[2].avg_temperature_celsius == Decimal("5.00")

    # The recent reading is untouched.
    remaining = list(
        admin_session.scalars(
            select(TemperatureReading).where(
                TemperatureReading.shipment_id == shipment.id
            )
        ).all()
    )
    assert len(remaining) == 1
    assert remaining[0].recorded_at == NOW - timedelta(hours=2)


def test_n3_64_a_running_shipment_is_never_compacted(
    admin_session: Session, identity_factory
):
    """The violation detector needs the raw series of a running shipment."""
    carrier = identity_factory(role="transporter", organization_type="transport")
    shipment = _seed_shipment(admin_session, carrier, completed=False)
    _add_reading(admin_session, shipment, NOW - timedelta(days=45), "4.00")

    summary = telemetry_compactor.compact_old_readings(
        admin_session, retention_days=30, now=NOW
    )

    assert summary["compacted_readings"] == 0
    rows = list(
        admin_session.scalars(
            select(TemperatureReading).where(
                TemperatureReading.shipment_id == shipment.id
            )
        ).all()
    )
    assert len(rows) == 1


def test_n3_64_the_hourly_series_is_readable(admin_session: Session, identity_factory):
    """The summarised hours are exposed for the shipment."""
    from app.core.auth import Principal
    from app.services import telemetry_service

    carrier = identity_factory(role="transporter", organization_type="transport")
    shipment = _seed_shipment(admin_session, carrier, completed=True)
    old = NOW - timedelta(days=45)
    _add_reading(admin_session, shipment, old, "4.00")
    _add_reading(admin_session, shipment, old + timedelta(minutes=5), "8.00")

    telemetry_compactor.compact_old_readings(admin_session, retention_days=30, now=NOW)

    principal = Principal(
        user_id=carrier.user_id,
        email=carrier.email,
        full_name="Integration test user",
        organization_id=carrier.organization_id,
        organization_name="Integration carrier",
        organization_type="transport",
        role="transporter",
    )
    series = telemetry_service.list_hourly_aggregates(
        admin_session, principal, shipment.id
    )
    assert len(series) == 1
    assert series[0].reading_count == 2
    assert series[0].max_temperature_celsius == Decimal("8.00")
    assert series[0].is_gap is False
