"""Privileged maintenance CLI; never exposed through the request API."""

import argparse
import logging
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.handover import Handover

logger = logging.getLogger(__name__)


def scan_overdue_handovers(
    db: Session, *, now: datetime | None = None, batch_size: int = 500
) -> int:
    """Mark pending requests in independent bounded transactions, without events."""
    if not 1 <= batch_size <= 10000:
        raise ValueError("batch_size must be between 1 and 10000")
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(hours=settings.HANDOVER_OVERDUE_HOURS)
    count = 0
    while True:
        candidates = (
            select(Handover.id)
            .where(
                Handover.status == "pending",
                Handover.overdue_at.is_(None),
                Handover.created_at < cutoff,
            )
            .order_by(Handover.created_at, Handover.id)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        try:
            result = db.execute(
                update(Handover)
                .where(Handover.id.in_(candidates))
                .values(overdue_at=now)
                .execution_options(synchronize_session=False)
            )
            changed = result.rowcount
            db.commit()
        except Exception:
            db.rollback()
            raise
        count += changed
        if changed == 0:
            return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Run one scan and exit")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    engine = create_engine(settings.MIGRATION_DATABASE_URL, pool_pre_ping=True)
    try:
        while True:
            try:
                with Session(engine) as db:
                    count = scan_overdue_handovers(db)
                logger.info("Marked %d overdue handovers", count)
            except Exception:
                logger.exception("Overdue handover scan failed")
                if args.once:
                    raise
            if args.once:
                return
            time.sleep(3600)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
