"""Event service implementing append-only event logging with SHA-256 hash chaining."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.core.crypto import GENESIS_PREV_HASH, compute_event_hash
from app.core.tenancy import get_tenant_record, tenant_select
from app.models.event import Event
from app.models.lot import Lot
from app.schemas.event import EventCreate


def record_event(
    db: Session,
    principal: Principal,
    event_in: EventCreate,
) -> Event:
    """Append a new immutable event to a lot's event chain.

    Ensures:
    1. Caller has access to the target lot within their organization.
    2. Sequence number is monotonic per lot.
    3. Cryptographic hash is chained to the previous event's hash (or genesis).
    4. The event is strictly append-only (no update or delete path exists).
    """
    # Verify lot exists and is visible to caller's organization
    lot = get_tenant_record(db, Lot, event_in.lot_id, principal)

    event = append_event(
        db,
        principal,
        lot.id,
        event_type=event_in.event_type,
        payload=event_in.payload,
    )
    db.commit()
    db.refresh(event)
    return event


def append_event(
    db: Session,
    principal: Principal,
    lot_id: UUID,
    *,
    event_type: str,
    payload: dict,
) -> Event:
    """Append an event without committing, for callers with a wider transaction."""
    # Query the latest event for this lot
    latest_event = db.scalar(
        select(Event)
        .where(
            Event.lot_id == lot_id,
            Event.organization_id == principal.organization_id,
        )
        .order_by(Event.sequence_number.desc())
        .limit(1)
    )

    if latest_event is None:
        sequence_number = 1
        prev_hash = GENESIS_PREV_HASH
    else:
        sequence_number = latest_event.sequence_number + 1
        prev_hash = latest_event.event_hash

    # Construct canonical content dictionary for hashing
    content_for_hash = {
        "event_type": event_type,
        "lot_id": str(lot_id),
        "organization_id": str(principal.organization_id),
        "payload": payload,
        "sequence_number": sequence_number,
    }
    event_hash = compute_event_hash(prev_hash, content_for_hash)

    event = Event(
        organization_id=principal.organization_id,
        lot_id=lot_id,
        sequence_number=sequence_number,
        event_type=event_type,
        payload=payload,
        prev_hash=prev_hash,
        event_hash=event_hash,
    )
    db.add(event)
    db.flush()
    return event


def list_events_for_lot(
    db: Session,
    principal: Principal,
    lot_id: UUID,
) -> list[Event]:
    """List all immutable events for a specific lot, ordered chronologically."""
    # Ensure lot is accessible
    get_tenant_record(db, Lot, lot_id, principal)

    return list(
        db.scalars(
            tenant_select(Event, principal)
            .where(Event.lot_id == lot_id)
            .order_by(Event.sequence_number.asc())
        ).all()
    )


def list_events(
    db: Session,
    principal: Principal,
    lot_id: UUID | None = None,
) -> list[Event]:
    """List the caller's accessible events, optionally for one visible lot."""
    if lot_id is not None:
        return list_events_for_lot(db, principal, lot_id)

    statement = tenant_select(Event, principal).order_by(Event.sequence_number.asc())
    return list(db.scalars(statement).all())


def get_event_by_id(
    db: Session,
    principal: Principal,
    event_id: UUID,
) -> Event:
    """Retrieve a single immutable event by ID, enforcing tenant isolation."""
    return get_tenant_record(db, Event, event_id, principal)
