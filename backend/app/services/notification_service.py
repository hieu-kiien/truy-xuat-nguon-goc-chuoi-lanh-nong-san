"""In-app notification centre (N3-56).

The service layer owns the notifications: it projects the items that still need
the caller's attention into ``notifications`` rows and returns them together
with the unread badge count. The interface only renders what the service
returns, and never creates a notification of its own.

Three kinds of item are projected:

* ``handover_pending`` — a lot handed over to the caller's organization and
  still waiting for a confirmation,
* ``recall_affected`` — an open recall order that touches a lot of the caller,
* ``cold_chain_violation`` — a cold chain excursion recorded on a lot the
  caller currently holds.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.models.event import Event
from app.models.handover import Handover
from app.models.lot import Lot
from app.models.notification import Notification
from app.schemas.notification import NotificationListRead, NotificationRead
from app.services import recall_service

logger = logging.getLogger(__name__)

HANDOVER_KIND = "handover_pending"
RECALL_KIND = "recall_affected"
VIOLATION_KIND = "cold_chain_violation"

VIOLATION_TYPE_LABELS = {
    "high_temp": "nhiệt độ cao",
    "low_temp": "nhiệt độ thấp",
}


@dataclass(frozen=True)
class ActionableItem:
    """One item that still needs the caller's attention."""

    kind: str
    source_key: str
    title: str
    body: str
    link_path: str
    lot_id: UUID | None
    lot_code: str | None
    created_at: datetime


def _pending_handover_items(db: Session, principal: Principal) -> list[ActionableItem]:
    """Handovers waiting for the caller's organization to confirm."""
    rows = db.execute(
        select(Handover, Lot)
        .join(Lot, Lot.id == Handover.lot_id)
        .where(
            Handover.to_organization_id == principal.organization_id,
            Handover.status == "pending",
        )
        .order_by(Handover.created_at.desc(), Handover.id.desc())
    ).all()

    items: list[ActionableItem] = []
    for handover, lot in rows:
        lot_label = lot.lot_code or lot.name
        items.append(
            ActionableItem(
                kind=HANDOVER_KIND,
                source_key=f"handover:{handover.id}",
                title="Bàn giao chờ xác nhận",
                body=f"Lô {lot_label} đang chờ tổ chức bạn xác nhận.",
                link_path="/handovers",
                lot_id=lot.id,
                lot_code=lot.lot_code,
                created_at=handover.created_at,
            )
        )
    return items


def _recall_items(db: Session, principal: Principal) -> list[ActionableItem]:
    """Open recall orders that affect lots of the caller's organization."""
    items: list[ActionableItem] = []
    for order in recall_service.list_recall_notifications(db, principal):
        if order.status != "open":
            continue
        lot_label = order.root_lot_code or order.root_lot_name or "lô gốc"
        items.append(
            ActionableItem(
                kind=RECALL_KIND,
                source_key=f"recall:{order.recall_id}",
                title="Lệnh thu hồi liên quan",
                body=f"Lệnh {order.recall_code} đang mở và ảnh hưởng lô {lot_label}.",
                link_path=f"/lots/{order.root_lot_id}",
                lot_id=order.root_lot_id,
                lot_code=order.root_lot_code,
                created_at=order.created_at,
            )
        )
    return items


def _violation_items(db: Session, principal: Principal) -> list[ActionableItem]:
    """Cold chain excursions recorded on lots the caller currently holds.

    The excursion is read from the immutable event chain because every lot on
    the shipment receives a ``cold_chain_violation`` event (N3-63). Reading it
    that way keeps the query inside the caller's own tenant scope.
    """
    rows = db.execute(
        select(Event, Lot)
        .join(Lot, Lot.id == Event.lot_id)
        .where(
            Event.event_type == "cold_chain_violation",
            Lot.current_holder_organization_id == principal.organization_id,
        )
        .order_by(Event.recorded_at.desc(), Event.sequence_number.desc())
    ).all()

    items: list[ActionableItem] = []
    seen: set[str] = set()
    for event, lot in rows:
        payload = event.payload or {}
        shipment_id = str(payload.get("shipment_id") or "")
        started_at = str(payload.get("started_at") or event.recorded_at.isoformat())
        source_key = f"violation:{shipment_id}:{started_at}"
        if source_key in seen:
            # The same excursion can touch several lots of the same holder.
            continue
        seen.add(source_key)

        violation_type = str(payload.get("violation_type") or "")
        label = VIOLATION_TYPE_LABELS.get(violation_type, violation_type or "nhiệt độ")
        try:
            minutes = float(payload.get("duration_minutes") or 0)
        except (TypeError, ValueError):
            minutes = 0.0
        shipment_code = str(payload.get("shipment_code") or "chuyến vận chuyển")
        lot_label = lot.lot_code or lot.name
        items.append(
            ActionableItem(
                kind=VIOLATION_KIND,
                source_key=source_key,
                title="Vi phạm chuỗi lạnh trên lô bạn giữ",
                body=(
                    f"Lô {lot_label} trên chuyến {shipment_code} bị vi phạm "
                    f"{label} trong {minutes:.0f} phút."
                ),
                link_path=f"/lots/{lot.id}",
                lot_id=lot.id,
                lot_code=lot.lot_code,
                created_at=event.recorded_at,
            )
        )
    return items


def actionable_items(db: Session, principal: Principal) -> list[ActionableItem]:
    """Collect every item that still needs the caller's attention."""
    return [
        *_pending_handover_items(db, principal),
        *_recall_items(db, principal),
        *_violation_items(db, principal),
    ]


def sync_notifications(
    db: Session, principal: Principal, items: list[ActionableItem]
) -> None:
    """Store the missing notifications for the caller.

    ``source_key`` keeps a notification stable, so the same underlying item
    never produces a second row for the same recipient.
    """
    known = set(
        db.scalars(
            select(Notification.source_key).where(
                Notification.recipient_user_id == principal.user_id
            )
        ).all()
    )
    added = False
    for item in items:
        if item.source_key in known:
            continue
        known.add(item.source_key)
        try:
            # Two tabs polling at the same time must not fail. The unique
            # constraint on (recipient, source_key) is the real guard, so a
            # conflicting insert is rolled back to its savepoint and skipped.
            with db.begin_nested():
                db.add(
                    Notification(
                        organization_id=principal.organization_id,
                        recipient_user_id=principal.user_id,
                        kind=item.kind,
                        source_key=item.source_key,
                        title=item.title,
                        body=item.body,
                        link_path=item.link_path,
                        lot_id=item.lot_id,
                        created_at=item.created_at,
                    )
                )
        except IntegrityError:
            continue
        added = True
    if added:
        db.flush()


def _serialize(
    row: Notification, lot_codes: dict[UUID, str | None]
) -> NotificationRead:
    return NotificationRead(
        id=row.id,
        kind=row.kind,
        title=row.title,
        body=row.body,
        link_path=row.link_path,
        lot_id=row.lot_id,
        lot_code=lot_codes.get(row.lot_id) if row.lot_id else None,
        created_at=row.created_at,
        read_at=row.read_at,
    )


def list_notifications(
    db: Session, principal: Principal, *, limit: int = 50
) -> NotificationListRead:
    """Return the notification centre content for the caller."""
    items = actionable_items(db, principal)
    sync_notifications(db, principal, items)
    db.commit()

    rows = list(
        db.scalars(
            select(Notification)
            .where(Notification.recipient_user_id == principal.user_id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
        ).all()
    )

    lot_codes: dict[UUID, str | None] = {}
    lot_ids = [row.lot_id for row in rows if row.lot_id is not None]
    if lot_ids:
        lot_codes = dict(
            db.execute(select(Lot.id, Lot.lot_code).where(Lot.id.in_(lot_ids))).all()
        )

    unread_count = (
        db.scalar(
            select(func.count(Notification.id)).where(
                Notification.recipient_user_id == principal.user_id,
                Notification.read_at.is_(None),
            )
        )
        or 0
    )

    return NotificationListRead(
        items=[_serialize(row, lot_codes) for row in rows],
        unread_count=int(unread_count),
        generated_at=datetime.now(UTC),
    )


def mark_read(
    db: Session, principal: Principal, notification_id: UUID
) -> NotificationRead:
    """Mark one notification of the caller as read."""
    row = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_user_id == principal.user_id,
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo.",
        )
    if row.read_at is None:
        row.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(row)
    lot_codes: dict[UUID, str | None] = {}
    if row.lot_id is not None:
        lot_codes = dict(
            db.execute(select(Lot.id, Lot.lot_code).where(Lot.id == row.lot_id)).all()
        )
    return _serialize(row, lot_codes)


def mark_all_read(db: Session, principal: Principal) -> int:
    """Mark every unread notification of the caller as read."""
    now = datetime.now(UTC)
    rows = list(
        db.scalars(
            select(Notification).where(
                Notification.recipient_user_id == principal.user_id,
                Notification.read_at.is_(None),
            )
        ).all()
    )
    for row in rows:
        row.read_at = now
    db.commit()
    return len(rows)
