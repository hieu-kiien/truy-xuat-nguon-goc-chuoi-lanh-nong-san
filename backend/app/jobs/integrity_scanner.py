"""Scheduled integrity scanner for every lot's event chain (N3-74).

Runs as a privileged maintenance process, never inside the request path, for
the same reason as ``jobs/overdue_handovers.py``: the scan has to read lots
and events of every organization and it has to record checks that no person
performed.

Two rules decide which lots are due for a check:

* a lot is due when it received new events since its last recorded check, or
* a lot is due when it was not checked during the current rotation window
  (7 days by default), so every lot is re-verified once per week.
"""

import argparse
import logging
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import create_engine, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.event import Event
from app.models.integrity_alert import IntegrityAlert
from app.models.integrity_check import IntegrityCheck
from app.models.lot import Lot
from app.services.event_service import verify_event_chain

logger = logging.getLogger(__name__)

DEFAULT_ROTATION_DAYS = 7
DEFAULT_BATCH_SIZE = 200


def _latest_checks(db: Session):
    """Latest recorded check per lot."""
    return select(
        IntegrityCheck.lot_id.label("lot_id"),
        IntegrityCheck.checked_at.label("checked_at"),
        IntegrityCheck.checked_events.label("checked_events"),
        IntegrityCheck.valid.label("valid"),
        func.row_number()
        .over(
            partition_by=IntegrityCheck.lot_id,
            order_by=IntegrityCheck.checked_at.desc(),
        )
        .label("row_number"),
    ).subquery()


def find_due_lots(
    db: Session,
    *,
    now: datetime | None = None,
    rotation_days: int = DEFAULT_ROTATION_DAYS,
    batch_size: int = DEFAULT_BATCH_SIZE,
    lot_ids: list[UUID] | None = None,
    include_all: bool = False,
) -> list[tuple[Lot, bool]]:
    """Return the lots that need a fresh integrity check.

    Each entry pairs the lot with the validity of its previous check, so the
    caller can tell a newly broken chain from a chain that was already broken.

    ``include_all`` checks every lot that owns events, regardless of the
    rotation. The recovery drill uses it to prove that every chain still
    verifies after a restore.
    """
    now = now or datetime.now(UTC)
    rotation_cutoff = now - timedelta(days=rotation_days)

    latest = _latest_checks(db)
    event_counts = (
        select(Event.lot_id.label("lot_id"), func.count(Event.id).label("event_count"))
        .group_by(Event.lot_id)
        .subquery()
    )

    statement = (
        select(
            Lot.id.label("lot_id"),
            Lot.current_holder_organization_id.label("holder_organization_id"),
            func.coalesce(event_counts.c.event_count, 0).label("event_count"),
            latest.c.checked_at.label("checked_at"),
            latest.c.checked_events.label("checked_events"),
            latest.c.valid.label("previous_valid"),
        )
        .outerjoin(event_counts, event_counts.c.lot_id == Lot.id)
        .outerjoin(latest, latest.c.lot_id == Lot.id)
        .where(or_(latest.c.lot_id.is_(None), latest.c.row_number == 1))
        .where(func.coalesce(event_counts.c.event_count, 0) > 0)
        .order_by(Lot.id)
        .limit(batch_size)
    )
    if lot_ids is not None:
        statement = statement.where(Lot.id.in_(lot_ids))
    if not include_all:
        statement = statement.where(
            or_(
                latest.c.lot_id.is_(None),
                latest.c.checked_at < rotation_cutoff,
                func.coalesce(event_counts.c.event_count, 0)
                > func.coalesce(latest.c.checked_events, 0),
            )
        )

    rows = db.execute(statement).all()
    due: list[tuple[Lot, bool]] = []
    for row in rows:
        lot = db.get(Lot, row.lot_id)
        if lot is None:
            continue
        previous_valid = (
            True if row.previous_valid is None else bool(row.previous_valid)
        )
        due.append((lot, previous_valid))
    return due


def check_lot_chain(db: Session, lot: Lot) -> dict:
    """Verify one lot's event chain without writing anything."""
    events = list(
        db.scalars(
            select(Event)
            .where(Event.lot_id == lot.id)
            .order_by(Event.sequence_number.asc())
        ).all()
    )
    return verify_event_chain(events)


def record_check(
    db: Session,
    lot: Lot,
    report: dict,
    *,
    detected_at: datetime | None = None,
) -> IntegrityCheck:
    """Append one integrity check produced by the scheduler."""
    detected_at = detected_at or datetime.now(UTC)
    check = IntegrityCheck(
        organization_id=lot.current_holder_organization_id,
        lot_id=lot.id,
        checked_by_user_id=None,
        checked_by_source="system",
        checked_at=detected_at,
        valid=report["valid"],
        checked_events=report["checked_events"],
        first_invalid_sequence=report["first_invalid_sequence"],
        issues=[issue.model_dump() for issue in report["issues"]],
    )
    db.add(check)
    db.flush()
    return check


def raise_alert(
    db: Session,
    lot: Lot,
    report: dict,
    *,
    detected_at: datetime | None = None,
) -> IntegrityAlert:
    """Append an alert for a chain that has just been found broken."""
    detected_at = detected_at or datetime.now(UTC)
    alert = IntegrityAlert(
        organization_id=lot.current_holder_organization_id,
        lot_id=lot.id,
        detected_at=detected_at,
        first_invalid_sequence=report["first_invalid_sequence"],
        issue_count=max(len(report["issues"]), 1),
        checked_events=report["checked_events"],
    )
    db.add(alert)
    db.flush()
    return alert


def run_integrity_scan(
    db: Session,
    *,
    now: datetime | None = None,
    rotation_days: int = DEFAULT_ROTATION_DAYS,
    batch_size: int = DEFAULT_BATCH_SIZE,
    lot_ids: list[UUID] | None = None,
    include_all: bool = False,
) -> dict:
    """Scan every due lot once and return a summary of the run."""
    now = now or datetime.now(UTC)
    due = find_due_lots(
        db,
        now=now,
        rotation_days=rotation_days,
        batch_size=batch_size,
        lot_ids=lot_ids,
        include_all=include_all,
    )

    checked = 0
    broken = 0
    alerts = 0
    for lot, previous_valid in due:
        report = check_lot_chain(db, lot)
        record_check(db, lot, report, detected_at=now)
        checked += 1
        if not report["valid"]:
            broken += 1
            # Only a newly broken chain raises an alert, so a lot that stays
            # broken does not flood the administrator view.
            if previous_valid:
                raise_alert(db, lot, report, detected_at=now)
                alerts += 1
                logger.warning(
                    "Integrity chain broken for lot %s at sequence %s",
                    lot.id,
                    report["first_invalid_sequence"],
                )
        db.commit()

    return {
        "checked_lots": checked,
        "broken_lots": broken,
        "alerts_raised": alerts,
        "scanned_at": now.isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Run one scan and exit")
    parser.add_argument(
        "--rotation-days",
        type=int,
        default=DEFAULT_ROTATION_DAYS,
        help="Re-verify every lot at least once per this many days",
    )
    parser.add_argument(
        "--interval-hours",
        type=int,
        default=24,
        help="Hours between two scans when running as a long-lived worker",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check every lot that owns events, ignoring the rotation window",
    )
    args = parser.parse_args()
    if not 1 <= args.rotation_days <= 365:
        raise ValueError("rotation-days must be between 1 and 365")
    if not 1 <= args.interval_hours <= 168:
        raise ValueError("interval-hours must be between 1 and 168")

    logging.basicConfig(level=logging.INFO)
    engine = create_engine(settings.MIGRATION_DATABASE_URL, pool_pre_ping=True)
    try:
        while True:
            try:
                with Session(engine) as db:
                    summary = run_integrity_scan(
                        db,
                        rotation_days=args.rotation_days,
                        include_all=args.all,
                    )
                logger.info("Integrity scan completed: %s", summary)
            except Exception:
                logger.exception("Integrity scan failed")
                if args.once:
                    raise
            if args.once:
                return
            time.sleep(args.interval_hours * 3600)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
