"""Event service implementing append-only event logging with SHA-256 hash chaining."""

from collections.abc import Iterable
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased, contains_eager

from app.core.auth import Principal
from app.core.crypto import GENESIS_PREV_HASH, compute_event_hash
from app.core.tenancy import get_tenant_record, tenant_select
from app.models.event import Event
from app.models.identity import Organization
from app.models.integrity_alert import IntegrityAlert
from app.models.integrity_check import IntegrityCheck
from app.models.lot import Lot
from app.schemas.event import EventCreate, EventRead, IntegrityIssue

# Payload keys that would put identifying data into the hashed content
# (N3-75). The chain must only reference entities by id, so that erasing a
# farmer's identity never breaks an existing hash.
FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "to_organization_name",
        "from_organization_name",
        "organization_name",
        "location_name",
        "location_address",
        "full_name",
        "email",
        "actor_email",
        "contact_email",
        "farm_name",
        "phone",
        "address",
        "actor_name",
    }
)


def _payload_keys(value) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                keys.add(key)
            keys.update(_payload_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_payload_keys(item))
    return keys


def assert_payload_has_no_identity(payload: dict) -> None:
    """Reject a payload that would hash identifying data into the chain."""
    offending = sorted(FORBIDDEN_PAYLOAD_KEYS.intersection(_payload_keys(payload)))
    if offending:
        raise HTTPException(
            400,
            "Sự kiện chỉ được tham chiếu định danh bằng mã, không ghi tên, "
            "email, số điện thoại hay địa chỉ vào chuỗi.",
        )


def _payload_lot_ids(value) -> set[UUID]:
    identifiers: set[UUID] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith("lot_id") and isinstance(item, str):
                try:
                    identifiers.add(UUID(item))
                except ValueError:
                    pass
            identifiers.update(_payload_lot_ids(item))
    elif isinstance(value, list):
        for item in value:
            identifiers.update(_payload_lot_ids(item))
    return identifiers


def readable_events(
    db: Session, principal: Principal, events: list[Event]
) -> list[EventRead]:
    """Project visibility without altering the canonical payload or its hash.

    Canonical events remain available to integrity verification in this service.
    Third-party ancestor logistics and inaccessible sibling references are hidden
    in every public read route, with an explicit flag on the display projection.
    """
    if not events:
        return []
    if principal.role in {"system_admin", "inspector"}:
        return [EventRead.model_validate(item) for item in events]
    references = [_payload_lot_ids(item.payload) for item in events]
    identifiers = {item.lot_id for item in events}.union(*references)
    holders = dict(
        db.execute(
            select(Lot.id, Lot.current_holder_organization_id).where(
                Lot.id.in_(identifiers)
            )
        ).all()
    )
    visible = holders.keys()
    result = []
    for item, refs in zip(events, references, strict=True):
        projected = EventRead.model_validate(item)
        third_party_source = (
            holders.get(item.lot_id) != principal.organization_id
            and item.organization_id != principal.organization_id
        )
        if third_party_source or not refs.issubset(visible):
            projected = projected.model_copy(
                update={"payload": {}, "payload_redacted": True}
            )
        result.append(projected)
    return result


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
    lot = db.scalar(
        select(Lot)
        .where(Lot.id == lot.id)
        .with_for_update(of=Lot)
        .execution_options(populate_existing=True)
    )
    if lot is None or lot.current_holder_organization_id != principal.organization_id:
        raise HTTPException(403, "Chỉ đơn vị đang giữ lô được ghi sự kiện.")
    if lot.status != "active":
        raise HTTPException(409, "Lô không ở trạng thái cho phép ghi sự kiện.")

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
    assert_payload_has_no_identity(payload)
    # Serialize appends per lot so concurrent writers cannot reuse a sequence.
    db.scalar(select(Lot).where(Lot.id == lot_id).with_for_update(of=Lot))

    latest_event = db.scalar(
        select(Event)
        .where(Event.lot_id == lot_id)
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
    get_tenant_record(db, Lot, lot_id, principal, allow_historical=True)

    return list(
        db.scalars(
            select(Event)
            .where(Event.lot_id == lot_id)
            .order_by(Event.sequence_number.asc())
        ).all()
    )


def list_events(
    db: Session,
    principal: Principal,
    lot_id: UUID | None = None,
) -> list[EventRead]:
    """List the caller's accessible events, optionally for one visible lot."""
    if lot_id is not None:
        return readable_events(
            db, principal, list_events_for_lot(db, principal, lot_id)
        )

    statement = tenant_select(Event, principal).order_by(Event.sequence_number.asc())
    return readable_events(db, principal, list(db.scalars(statement).all()))


def verify_event_chain(events: Iterable[Event]) -> dict:
    """Recompute a lot's complete chain in memory and identify the first break."""
    expected_previous_hash = GENESIS_PREV_HASH
    expected_sequence = 1
    issues: list[IntegrityIssue] = []
    invalid_sequence: int | None = None
    count = 0

    for event in events:
        count += 1
        if invalid_sequence is not None:
            if event.sequence_number > invalid_sequence:
                issues.append(
                    IntegrityIssue(
                        sequence_number=event.sequence_number,
                        kind="downstream_unverified",
                    )
                )
            continue
        if event.sequence_number != expected_sequence:
            missing_at = min(event.sequence_number, expected_sequence)
            issues.append(
                IntegrityIssue(sequence_number=missing_at, kind="missing_event")
            )
            invalid_sequence = missing_at
            if event.sequence_number > missing_at:
                issues.append(
                    IntegrityIssue(
                        sequence_number=event.sequence_number,
                        kind="downstream_unverified",
                    )
                )
            continue

        if event.prev_hash != expected_previous_hash:
            issues.append(
                IntegrityIssue(
                    sequence_number=event.sequence_number,
                    kind="previous_hash_mismatch",
                )
            )
            invalid_sequence = event.sequence_number
            continue

        event_content = {
            "event_type": event.event_type,
            "lot_id": str(event.lot_id),
            "organization_id": str(event.organization_id),
            "payload": event.payload,
            "sequence_number": event.sequence_number,
        }
        expected_hash = compute_event_hash(event.prev_hash, event_content)
        if event.event_hash != expected_hash:
            issues.append(
                IntegrityIssue(
                    sequence_number=event.sequence_number,
                    kind="content_hash_mismatch",
                )
            )
            invalid_sequence = event.sequence_number
            continue

        expected_previous_hash = event.event_hash
        expected_sequence += 1

    return {
        "valid": not issues,
        "checked_events": count,
        "first_invalid_sequence": invalid_sequence,
        "issues": issues,
    }


def get_event_history(
    db: Session,
    principal: Principal,
    lot_id: UUID,
    *,
    after: int = 0,
    page_size: int = 500,
) -> dict:
    """Stream full verification in one event query, retain only the requested page."""
    get_tenant_record(db, Lot, lot_id, principal, allow_historical=True)
    # Evaluate organization RLS once, even if PostgreSQL chooses a nested-loop
    # join for a small organization table and hundreds of history events.
    visible_organizations = (
        select(Organization).cte("history_organizations").prefix_with("MATERIALIZED")
    )
    organization = aliased(Organization, visible_organizations)
    statement = (
        select(Event)
        .outerjoin(organization, Event.organization_id == organization.id)
        .options(contains_eager(Event.organization, alias=organization))
        .where(Event.lot_id == lot_id)
        .order_by(Event.sequence_number.asc())
        .execution_options(yield_per=100)
    )
    events = []
    has_more = False

    def full_chain():
        nonlocal has_more
        for event in db.scalars(statement):
            if event.sequence_number > after:
                if len(events) < page_size:
                    events.append(event)
                else:
                    has_more = True
            yield event

    integrity = verify_event_chain(full_chain())
    return {
        "events": readable_events(db, principal, events),
        "integrity": integrity,
        "next_cursor": events[-1].sequence_number if events and has_more else None,
        "total": integrity["checked_events"],
    }


def verify_lot_integrity(db: Session, principal: Principal, lot_id: UUID) -> dict:
    get_tenant_record(db, Lot, lot_id, principal)
    events = list(
        db.scalars(
            select(Event)
            .where(Event.lot_id == lot_id)
            .order_by(Event.sequence_number.asc())
        ).all()
    )
    return verify_event_chain(events)


def record_integrity_check(db: Session, principal: Principal, lot_id: UUID) -> dict:
    """Verify a lot and append an immutable, timestamped audit record."""
    lot = get_tenant_record(db, Lot, lot_id, principal)
    events = list(
        db.scalars(
            select(Event)
            .where(Event.lot_id == lot_id)
            .order_by(Event.sequence_number.asc())
        ).all()
    )
    report = verify_event_chain(events)
    check = IntegrityCheck(
        organization_id=principal.organization_id,
        lot_id=lot.id,
        checked_by_user_id=principal.user_id,
        valid=report["valid"],
        checked_events=report["checked_events"],
        first_invalid_sequence=report["first_invalid_sequence"],
        issues=[issue.model_dump() for issue in report["issues"]],
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return {
        "id": check.id,
        "lot_id": check.lot_id,
        "checked_at": check.checked_at,
        **report,
    }


def get_integrity_check_history(
    db: Session, principal: Principal, lot_id: UUID, limit: int = 10
) -> list[IntegrityCheck]:
    """Return recent verification records visible to the caller."""
    get_tenant_record(db, Lot, lot_id, principal)
    statement = select(IntegrityCheck).where(IntegrityCheck.lot_id == lot_id)
    if principal.role not in {"inspector", "system_admin"}:
        statement = statement.where(
            IntegrityCheck.organization_id == principal.organization_id
        )
    return list(
        db.scalars(
            statement.order_by(IntegrityCheck.checked_at.desc()).limit(limit)
        ).all()
    )


def summarize_integrity_scans(
    db: Session, principal: Principal, *, limit: int = 20
) -> dict:
    """Summarize the scheduled integrity scans for the administrator view.

    Reports the most recent scan time, how many lots carry a recorded check
    and how many of them are currently broken. Row level security decides
    which checks and alerts the caller may see.
    """
    latest = select(
        IntegrityCheck.lot_id.label("lot_id"),
        IntegrityCheck.organization_id.label("organization_id"),
        IntegrityCheck.valid.label("valid"),
        IntegrityCheck.checked_at.label("checked_at"),
        IntegrityCheck.checked_events.label("checked_events"),
        IntegrityCheck.first_invalid_sequence.label("first_invalid_sequence"),
        func.row_number()
        .over(
            partition_by=IntegrityCheck.lot_id,
            order_by=IntegrityCheck.checked_at.desc(),
        )
        .label("row_number"),
    ).subquery()
    rows = db.execute(
        select(
            latest.c.lot_id,
            latest.c.organization_id,
            latest.c.valid,
            latest.c.checked_at,
            latest.c.checked_events,
            latest.c.first_invalid_sequence,
        )
        .where(latest.c.row_number == 1)
        .order_by(latest.c.checked_at.desc())
    ).all()

    broken_rows = [row for row in rows if not row.valid]
    last_checked_at = rows[0].checked_at if rows else None

    lot_codes = _lot_codes(db, [row.lot_id for row in broken_rows])

    broken_lots = [
        {
            "id": row.lot_id,
            "lot_id": row.lot_id,
            "lot_code": lot_codes.get(row.lot_id),
            "organization_id": row.organization_id,
            "detected_at": row.checked_at,
            "first_invalid_sequence": row.first_invalid_sequence,
            "issue_count": 1,
            "checked_events": row.checked_events,
        }
        for row in broken_rows
    ]

    alerts = list(
        db.scalars(
            select(IntegrityAlert)
            .order_by(IntegrityAlert.detected_at.desc())
            .limit(limit)
        ).all()
    )
    alert_lot_codes = _lot_codes(db, [alert.lot_id for alert in alerts])

    recent_alerts = [
        {
            "id": alert.id,
            "lot_id": alert.lot_id,
            "lot_code": alert_lot_codes.get(alert.lot_id),
            "organization_id": alert.organization_id,
            "detected_at": alert.detected_at,
            "first_invalid_sequence": alert.first_invalid_sequence,
            "issue_count": alert.issue_count,
            "checked_events": alert.checked_events,
        }
        for alert in alerts
    ]

    return {
        "generated_at": datetime.now(UTC),
        "last_checked_at": last_checked_at,
        "checked_lot_count": len(rows),
        "broken_lot_count": len(broken_rows),
        "broken_lots": broken_lots,
        "recent_alerts": recent_alerts,
    }


def _lot_codes(db: Session, lot_ids: list[UUID]) -> dict[UUID, str | None]:
    """Resolve the human readable lot codes for a set of lots."""
    if not lot_ids:
        return {}
    rows = db.execute(select(Lot.id, Lot.lot_code).where(Lot.id.in_(lot_ids))).all()
    return {row.id: row.lot_code for row in rows}


def get_event_by_id(
    db: Session,
    principal: Principal,
    event_id: UUID,
) -> EventRead:
    """Retrieve a single immutable event by ID, enforcing tenant isolation."""
    original = get_tenant_record(db, Event, event_id, principal)
    return readable_events(db, principal, [original])[0]
