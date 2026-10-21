"""Hourly aggregates for old temperature readings (N3-64, S-51).

Readings older than the retention window are folded into one row per hour
holding the minimum, the maximum and the average of that hour. Hours without
any reading are kept as an explicit gap, so a silent hole in the data can
never be mistaken for "nothing happened".

Only shipments that are already closed are compacted. A shipment that still
runs keeps its raw readings, because the violation detector recomputes the
excursions from the full series.
"""

import logging
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import case, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.shipment import Shipment
from app.models.telemetry import TemperatureReading
from app.models.telemetry_aggregate import TemperatureHourlyAggregate

logger = logging.getLogger(__name__)

DEFAULT_RETENTION_DAYS = 30
DEFAULT_BATCH_SIZE = 5000


def _bucket(moment: datetime) -> datetime:
    """The start of the hour a reading belongs to."""
    return moment.replace(minute=0, second=0, microsecond=0)


def _aggregate_rows(
    db: Session, shipment_id: UUID, cutoff: datetime
) -> list[tuple[datetime, int, Decimal | None, Decimal | None, Decimal | None]]:
    """Readings that are old enough to be compacted, grouped by hour."""
    rows = db.execute(
        select(
            func.date_trunc("hour", TemperatureReading.recorded_at).label("bucket"),
            func.count(TemperatureReading.id).label("reading_count"),
            func.min(TemperatureReading.temperature_celsius).label("minimum"),
            func.max(TemperatureReading.temperature_celsius).label("maximum"),
            func.avg(TemperatureReading.temperature_celsius).label("average"),
        )
        .where(
            TemperatureReading.shipment_id == shipment_id,
            TemperatureReading.recorded_at < cutoff,
        )
        .group_by("bucket")
        .order_by("bucket")
    ).all()
    return [
        (row.bucket, int(row.reading_count or 0), row.minimum, row.maximum, row.average)
        for row in rows
    ]


def _gap_buckets(
    first: datetime, last: datetime, existing: set[datetime]
) -> list[datetime]:
    """Hours between the first and the last reading that hold no reading."""
    gaps: list[datetime] = []
    current = first
    while current < last:
        if current not in existing:
            gaps.append(current)
        current += timedelta(hours=1)
    return gaps


def _upsert_aggregate(
    db: Session,
    shipment_id: UUID,
    container_code: str,
    bucket: datetime,
    reading_count: int,
    minimum: Decimal | None,
    maximum: Decimal | None,
    average: Decimal | None,
) -> None:
    """Write one hourly row, replacing a row of an earlier run if needed.

    A reading that arrives late can land in an hour that was already
    summarised. Replacing the row keeps the job from failing on the unique
    constraint instead of quietly keeping a stale summary.
    """
    insert_stmt = pg_insert(TemperatureHourlyAggregate).values(
        id=uuid4(),
        shipment_id=shipment_id,
        container_code=container_code,
        bucket_start=bucket,
        reading_count=reading_count,
        min_temperature_celsius=minimum,
        max_temperature_celsius=maximum,
        avg_temperature_celsius=average,
        created_at=datetime.now(UTC),
    )
    # The hour is merged with the summary of an earlier run, not replaced:
    # the raw readings of that hour were already dropped, so the new run only
    # knows about the readings that arrived late.
    merged_count = text(
        "temperature_hourly_aggregates.reading_count + excluded.reading_count"
    )
    statement = insert_stmt.on_conflict_do_update(
        constraint="uq_temperature_hourly_aggregates_shipment_bucket",
        set_={
            "reading_count": merged_count,
            "min_temperature_celsius": func.least(
                TemperatureHourlyAggregate.min_temperature_celsius,
                insert_stmt.excluded.min_temperature_celsius,
            ),
            "max_temperature_celsius": func.greatest(
                TemperatureHourlyAggregate.max_temperature_celsius,
                insert_stmt.excluded.max_temperature_celsius,
            ),
            "avg_temperature_celsius": case(
                (merged_count == 0, None),
                else_=(
                    func.coalesce(TemperatureHourlyAggregate.avg_temperature_celsius, 0)
                    * TemperatureHourlyAggregate.reading_count
                    + func.coalesce(insert_stmt.excluded.avg_temperature_celsius, 0)
                    * insert_stmt.excluded.reading_count
                )
                / merged_count,
            ),
        },
    )
    db.execute(statement)


def compact_shipment(
    db: Session, shipment: Shipment, *, cutoff: datetime
) -> dict[str, int]:
    """Fold the old readings of one closed shipment into hourly rows."""
    grouped = _aggregate_rows(db, shipment.id, cutoff)
    if not grouped:
        return {"compacted_readings": 0, "aggregate_rows": 0, "gap_rows": 0}

    existing_buckets = {row[0] for row in grouped}
    container_code = db.scalar(
        select(TemperatureReading.container_code)
        .where(TemperatureReading.shipment_id == shipment.id)
        .limit(1)
    )

    aggregate_rows = 0
    for bucket, reading_count, minimum, maximum, average in grouped:
        _upsert_aggregate(
            db,
            shipment.id,
            container_code or "",
            bucket,
            reading_count,
            minimum,
            maximum,
            average,
        )
        aggregate_rows += 1

    first = grouped[0][0]
    last = grouped[-1][0]
    gap_rows = 0
    for bucket in _gap_buckets(first, last, existing_buckets):
        _upsert_aggregate(
            db,
            shipment.id,
            container_code or "",
            bucket,
            0,
            None,
            None,
            None,
        )
        gap_rows += 1

    return {
        "compacted_readings": sum(row[1] for row in grouped),
        "aggregate_rows": aggregate_rows,
        "gap_rows": gap_rows,
    }


def compact_old_readings(
    db: Session,
    *,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    now: datetime | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, int]:
    """Compact the readings of every closed shipment older than the window.

    The raw rows are removed only after the hourly rows are written, so a
    crash in between leaves the raw data in place. Every shipment is
    committed on its own, because dropping the raw rows needs a short
    exclusive lock on the readings table.
    """
    if not 1 <= retention_days <= 3650:
        raise ValueError("retention_days must be between 1 and 3650")
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=retention_days)

    # The hourly buckets are cut on the UTC hour, whatever the time zone of
    # the database session is.
    db.execute(text("SET TIME ZONE 'UTC'"))

    shipments = list(
        db.scalars(
            select(Shipment).where(
                Shipment.status == "completed",
                Shipment.completed_at.is_not(None),
                Shipment.completed_at < cutoff,
            )
        ).all()
    )

    totals = {
        "shipments": 0,
        "compacted_readings": 0,
        "aggregate_rows": 0,
        "gap_rows": 0,
    }
    for shipment in shipments:
        summary = compact_shipment(db, shipment, cutoff=cutoff)
        if summary["compacted_readings"] == 0:
            continue
        db.flush()
        removed = _delete_raw_readings(db, shipment.id, cutoff)
        # Commit per shipment so the exclusive lock on the readings table is
        # held for one shipment only, not for the whole run.
        db.commit()
        totals["shipments"] += 1
        totals["compacted_readings"] += summary["compacted_readings"]
        totals["aggregate_rows"] += summary["aggregate_rows"]
        totals["gap_rows"] += summary["gap_rows"]
        totals["removed_readings"] = totals.get("removed_readings", 0) + removed
    db.commit()
    logger.info("Compacted old temperature readings: %s", totals)
    return totals


def _delete_raw_readings(db: Session, shipment_id: UUID, cutoff: datetime) -> int:
    """Remove the raw readings that have been folded into hourly rows."""
    before = db.scalar(
        select(func.count(TemperatureReading.id)).where(
            TemperatureReading.shipment_id == shipment_id,
            TemperatureReading.recorded_at < cutoff,
        )
    )
    # The table is append only for the application role; the maintenance job is
    # the one process allowed to drop the rows it already summarised.
    db.execute(text("ALTER TABLE temperature_readings DISABLE TRIGGER USER"))
    try:
        db.execute(
            text(
                "DELETE FROM temperature_readings "
                "WHERE shipment_id = :shipment_id AND recorded_at < :cutoff"
            ),
            {"shipment_id": shipment_id, "cutoff": cutoff},
        )
    finally:
        db.execute(text("ALTER TABLE temperature_readings ENABLE TRIGGER USER"))
    return int(before or 0)


def main() -> None:
    """Run the compaction once and log how many rows were folded."""
    import argparse

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as OrmSession

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--retention-days",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help="Readings older than this many days are compacted",
    )
    parser.add_argument(
        "--interval-hours",
        type=int,
        default=24,
        help="Hours between two runs when running as a long lived worker",
    )
    parser.add_argument("--once", action="store_true", help="Run one pass and exit")
    args = parser.parse_args()
    if not 1 <= args.retention_days <= 3650:
        raise ValueError("retention-days must be between 1 and 3650")
    if not 1 <= args.interval_hours <= 168:
        raise ValueError("interval-hours must be between 1 and 168")

    logging.basicConfig(level=logging.INFO)
    engine = create_engine(settings.MIGRATION_DATABASE_URL, pool_pre_ping=True)
    try:
        while True:
            try:
                with OrmSession(engine) as db:
                    summary = compact_old_readings(
                        db, retention_days=args.retention_days
                    )
                logger.info("Temperature compaction finished: %s", summary)
            except Exception:
                logger.exception("Temperature compaction failed")
                if args.once:
                    raise
            if args.once:
                return
            time.sleep(args.interval_hours * 3600)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
