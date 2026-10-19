"""Service layer for managing product recalls and blocking affected lots."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.core.lot_codes import generate_lot_code
from app.models.lot import Lot
from app.models.recall_order import DEFAULT_RECALL_REASON, RecallOrder, RecallOrderLot
from app.schemas.recall import RecallCreate, RecallOrderCreate
from app.services import event_service


def _generate_recall_code(db: Session) -> str:
    """Generate a collision-resistant human-readable recall code."""
    year = datetime.now(UTC).year
    for _ in range(5):
        candidate = f"RC-{year}-{generate_lot_code()[:6]}"
        exists = db.scalar(
            select(RecallOrder.id).where(RecallOrder.recall_code == candidate)
        )
        if not exists:
            return candidate
    raise RuntimeError("Không thể tạo mã thu hồi duy nhất, vui lòng thử lại.")


def get_blocking_recall(db: Session, lot_id: UUID) -> RecallOrder | None:
    """Return the recall order currently blocking this lot, or None.

    A lot is blocked when:
    1. It is explicitly listed in recall_order_lots of an open recall order, OR
       a completed recall order where incident_flag is still True.
    2. Or the lot itself (or one of its ancestors in lot_relations) is the
       root_lot_id of an open recall order (when no explicit incident_flag=False
       override exists).
    """
    explicit_entry = db.execute(
        select(RecallOrder, RecallOrderLot)
        .join(RecallOrderLot, RecallOrderLot.recall_order_id == RecallOrder.id)
        .where(RecallOrderLot.lot_id == lot_id)
        .order_by(RecallOrder.created_at.desc())
    ).first()

    if explicit_entry is not None:
        order, lot_entry = explicit_entry
        if order.status == "open" or (
            order.status == "completed" and lot_entry.incident_flag
        ):
            return order
        return None

    # Check if lot_id or any ancestor in lot_relations has an open RecallOrder
    ancestor_stmt = text("""
        WITH RECURSIVE ancestors(id) AS (
            SELECT CAST(:lot_id AS uuid)
            UNION
            SELECT r.parent_lot_id
            FROM lot_relations r
            JOIN ancestors a ON r.child_lot_id = a.id
        )
        SELECT ro.id
        FROM recall_orders ro
        WHERE ro.status = 'open'
          AND ro.root_lot_id IN (SELECT id FROM ancestors)
        ORDER BY ro.created_at DESC
        LIMIT 1
    """)
    blocking_id = db.execute(ancestor_stmt, {"lot_id": lot_id}).scalar()
    if blocking_id is not None:
        return db.get(RecallOrder, blocking_id)
    return None


def raise_if_recall_blocked(db: Session, lot_id: UUID) -> None:
    """Raise 409 with the recall order code if the lot is blocked."""
    blocking = get_blocking_recall(db, lot_id)
    if blocking is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Lô đang bị thu hồi. Mã lệnh thu hồi: {blocking.recall_code}. "
                "Vui lòng liên hệ quản trị viên."
            ),
        )


def open_recall(
    db: Session,
    principal: Principal,
    payload: RecallCreate,
) -> RecallOrder:
    """Open a new recall order for a compromised lot (N3-49)."""
    if principal.role not in {"inspector", "system_admin", "organization_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ cán bộ kiểm tra hoặc quản trị tổ chức đang giữ lô được mở lệnh thu hồi.",
        )

    lot = db.get(Lot, payload.lot_id)
    if lot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lô hàng yêu cầu thu hồi.",
        )

    if principal.role == "organization_admin":
        if lot.current_holder_organization_id != principal.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Quản trị viên chỉ được mở lệnh thu hồi cho lô do tổ chức mình đang giữ.",
            )

    if lot.status == "consumed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Không thể mở lệnh thu hồi trực tiếp trên lô đã tiêu thụ hết.",
        )

    existing_open = db.scalar(
        select(RecallOrder).where(
            RecallOrder.root_lot_id == lot.id,
            RecallOrder.status == "open",
        )
    )
    if existing_open is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "RECALL_ALREADY_OPEN",
                "message": f"Lô này đã có lệnh thu hồi đang mở ({existing_open.recall_code}).",
                "recall_id": str(existing_open.id),
                "recall_code": existing_open.recall_code,
            },
        )

    recall_code = _generate_recall_code(db)
    order = RecallOrder(
        recall_code=recall_code,
        root_lot_id=lot.id,
        opened_by_user_id=principal.user_id,
        opened_by_organization_id=principal.organization_id,
        reason=payload.reason,
        status="open",
    )
    db.add(order)
    db.flush()

    db.add(
        RecallOrderLot(
            recall_order_id=order.id,
            organization_id=principal.organization_id,
            lot_id=lot.id,
            incident_flag=True,
        )
    )
    db.flush()

    event_service.append_event(
        db,
        principal,
        lot.id,
        event_type="recall_opened",
        payload={
            "recall_id": str(order.id),
            "recall_code": order.recall_code,
            "reason": order.reason,
            "opened_by_role": principal.role,
            "opened_by_organization_id": str(principal.organization_id),
        },
    )

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        conflict = db.scalar(
            select(RecallOrder).where(
                RecallOrder.root_lot_id == lot.id,
                RecallOrder.status == "open",
            )
        )
        if conflict is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "RECALL_ALREADY_OPEN",
                    "message": f"Lô này đã có lệnh thu hồi đang mở ({conflict.recall_code}).",
                    "recall_id": str(conflict.id),
                    "recall_code": conflict.recall_code,
                },
            ) from exc
        raise

    db.refresh(order)
    return order


def create_recall_order(
    db: Session, principal: Principal, payload: RecallOrderCreate
) -> RecallOrder:
    """Create a recall order with explicit code and lot list (N3-53)."""
    existing = db.scalar(
        select(RecallOrder).where(RecallOrder.recall_code == payload.code)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Mã lệnh thu hồi {payload.code} đã tồn tại.",
        )

    lots = list(
        db.scalars(
            select(Lot).where(
                Lot.id.in_(payload.lot_ids),
                Lot.current_holder_organization_id == principal.organization_id,
            )
        ).all()
    )
    if len(lots) != len(payload.lot_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Một hoặc nhiều lô không thuộc tổ chức đang giữ.",
        )

    reason_text = (payload.note or "").strip()
    if len(reason_text) < 20:
        reason_text = DEFAULT_RECALL_REASON

    order = RecallOrder(
        recall_code=payload.code,
        root_lot_id=lots[0].id,
        opened_by_user_id=principal.user_id,
        opened_by_organization_id=principal.organization_id,
        reason=reason_text,
        status="open",
    )
    db.add(order)
    db.flush()

    for lot in lots:
        db.add(
            RecallOrderLot(
                recall_order_id=order.id,
                organization_id=principal.organization_id,
                lot_id=lot.id,
                incident_flag=True,
            )
        )

    db.flush()
    for lot in lots:
        event_service.append_event(
            db,
            principal,
            lot.id,
            event_type="recall_opened",
            payload={
                "recall_id": str(order.id),
                "recall_code": order.recall_code,
                "reason": order.reason,
                "opened_by_role": principal.role,
                "opened_by_organization_id": str(principal.organization_id),
            },
        )
    db.commit()
    db.refresh(order)
    return order


def list_recalls(
    db: Session, principal: Principal, *, status_filter: str | None = None
) -> list[RecallOrder]:
    """List recall orders visible to the principal."""
    stmt = select(RecallOrder).order_by(RecallOrder.created_at.desc())

    if principal.role not in {"inspector", "system_admin"}:
        stmt = stmt.join(RecallOrder.root_lot).where(
            (RecallOrder.opened_by_organization_id == principal.organization_id)
            | (Lot.current_holder_organization_id == principal.organization_id)
        )
    if status_filter:
        stmt = stmt.where(RecallOrder.status == status_filter)

    return list(db.scalars(stmt).all())


def list_recall_orders(
    db: Session, principal: Principal, *, status_filter: str | None = None
) -> list[RecallOrder]:
    """Alias for list_recalls supporting status_filter."""
    return list_recalls(db, principal, status_filter=status_filter)


def get_recall(db: Session, principal: Principal, recall_id: UUID) -> RecallOrder:
    """Get details of a single recall order."""
    order = db.get(RecallOrder, recall_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lệnh thu hồi.",
        )

    if principal.role not in {"inspector", "system_admin"}:
        is_opener = order.opened_by_organization_id == principal.organization_id
        is_holder = bool(
            order.root_lot
            and order.root_lot.current_holder_organization_id
            == principal.organization_id
        )
        if not (is_opener or is_holder):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền xem lệnh thu hồi này.",
            )

    return order


def complete_recall_order(
    db: Session, principal: Principal, recall_order_id: UUID
) -> RecallOrder:
    """Mark a recall order as completed."""
    order = get_recall(db, principal, recall_order_id)
    if order.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lệnh thu hồi đã hoàn tất từ trước.",
        )

    order.status = "completed"
    order.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(order)
    return order


def update_incident_flag(
    db: Session,
    principal: Principal,
    recall_order_id: UUID,
    lot_id: UUID,
    incident_flag: bool,
) -> None:
    """Update the incident flag for a lot within a recall order."""
    entry = db.scalar(
        select(RecallOrderLot).where(
            RecallOrderLot.recall_order_id == recall_order_id,
            RecallOrderLot.lot_id == lot_id,
        )
    )
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lô trong lệnh thu hồi.",
        )

    order = db.get(RecallOrder, recall_order_id)
    if order is None or (
        principal.role not in {"inspector", "system_admin"}
        and order.opened_by_organization_id != principal.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lệnh thu hồi.",
        )

    entry.incident_flag = incident_flag
    db.commit()
