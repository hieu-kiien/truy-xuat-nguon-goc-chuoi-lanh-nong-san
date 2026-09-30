import secrets
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.core.tenancy import get_tenant_record, tenant_select
from app.models.catalog import Product
from app.models.farm import Farm
from app.models.traceability import Lot, LotEvent, LotLineage
from app.schemas.traceability import (
    LotCreate,
    LotDeriveCreate,
    LotEventCreate,
    LotEventRead,
    LotLineageRead,
    LotRead,
    LotStatus,
    Page,
)

router = APIRouter()
TERMINAL_STATUSES = {LotStatus.sold, LotStatus.discarded}
STATUS_AFTER_EVENT = {
    "harvested": (LotStatus.created, LotStatus.harvested),
    "processed": (LotStatus.harvested, LotStatus.processed),
    "packed": (LotStatus.processed, LotStatus.packed),
    "stored": ((LotStatus.packed, LotStatus.received), LotStatus.stored),
    "sold": (LotStatus.stored, LotStatus.sold),
}


def _get_lot(db: Session, lot_id: UUID, principal: Principal) -> Lot:
    statement = tenant_select(Lot, principal, allow_cross_tenant_read=True).where(
        Lot.id == lot_id
    )
    lot = db.scalar(statement)
    if lot is not None:
        return lot
    return get_tenant_record(db, Lot, lot_id, principal)


def _event(
    lot: Lot,
    principal: Principal,
    event_type: str,
    occurred_at: datetime,
    public_note: str | None = None,
    details: dict | None = None,
) -> LotEvent:
    if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
        raise HTTPException(status_code=422, detail="occurred_at phải có múi giờ.")
    return LotEvent(
        lot_id=lot.id,
        # The event belongs to the organization that currently custodies the
        # lot, not to whoever happened to write the event. Custody transfers
        # move `lots.organization_id`, so deriving this from the lot keeps the
        # append-only provenance history consistent.
        organization_id=lot.organization_id,
        actor_user_id=principal.user_id,
        event_type=event_type,
        occurred_at=occurred_at,
        public_note=public_note,
        details=details or {},
    )


@router.get("/", response_model=Page[LotRead])
@require_permission("lots:read")
def list_lots(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    status_filter: Annotated[LotStatus | None, Query(alias="status")] = None,
) -> Page[LotRead]:
    base = tenant_select(Lot, principal, allow_cross_tenant_read=True)
    if status_filter is not None:
        base = base.where(Lot.status == status_filter.value)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    lots = db.scalars(
        base.order_by(Lot.created_at.desc(), Lot.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(items=list(lots), page=page, page_size=page_size, total=total)


@router.post("/", response_model=LotRead, status_code=status.HTTP_201_CREATED)
@require_permission("lots:write")
def create_lot(
    payload: LotCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Lot:
    get_tenant_record(db, Product, payload.product_id, principal)
    get_tenant_record(db, Farm, payload.origin_farm_id, principal)
    if payload.harvested_at is not None and (
        payload.harvested_at.tzinfo is None or payload.harvested_at.utcoffset() is None
    ):
        raise HTTPException(status_code=422, detail="harvested_at phải có múi giờ.")

    initial_status = (
        LotStatus.harvested.value
        if payload.harvested_at is not None
        else LotStatus.created.value
    )
    lot = Lot(
        public_code=secrets.token_urlsafe(32),
        lot_number=payload.lot_number,
        organization_id=principal.organization_id,
        origin_organization_id=principal.organization_id,
        product_id=payload.product_id,
        origin_farm_id=payload.origin_farm_id,
        quantity=payload.quantity,
        unit=payload.unit.strip(),
        status=initial_status,
        harvested_at=payload.harvested_at,
        created_by_id=principal.user_id,
    )
    db.add(lot)
    db.flush()
    db.add(
        _event(
            lot,
            principal,
            "lot_created",
            datetime.now(UTC),
            payload.public_note,
        )
    )
    if payload.harvested_at is not None:
        db.add(
            _event(
                lot,
                principal,
                "harvested",
                payload.harvested_at,
                payload.public_note,
            )
        )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Mã lô đã tồn tại trong tổ chức."
        ) from error
    db.refresh(lot)
    return lot


@router.get("/{lot_id}", response_model=LotRead)
@require_permission("lots:read")
def get_lot(
    lot_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Lot:
    return _get_lot(db, lot_id, principal)


@router.get("/{lot_id}/events", response_model=Page[LotEventRead])
@require_permission("lots:read")
def list_lot_events(
    lot_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> Page[LotEventRead]:
    lot = _get_lot(db, lot_id, principal)
    base = select(LotEvent).where(LotEvent.lot_id == lot.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    events = db.scalars(
        base.order_by(LotEvent.occurred_at.desc(), LotEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(items=list(events), page=page, page_size=page_size, total=total)


@router.post("/{lot_id}/events", response_model=LotEventRead, status_code=201)
@require_permission("lots:write")
def add_lot_event(
    lot_id: UUID,
    payload: LotEventCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> LotEvent:
    lot = db.scalar(
        tenant_select(Lot, principal).where(Lot.id == lot_id).with_for_update()
    )
    if lot is None:
        return get_tenant_record(db, Lot, lot_id, principal)

    if payload.event_type.value == "inspection":
        pass
    elif payload.event_type.value == "discarded":
        if lot.status in TERMINAL_STATUSES or lot.status == LotStatus.in_transit:
            raise HTTPException(status_code=409, detail="Trạng thái lô không thể hủy.")
        lot.status = LotStatus.discarded.value
    else:
        source_status, target_status = STATUS_AFTER_EVENT[payload.event_type.value]
        valid_sources = (
            source_status if isinstance(source_status, tuple) else (source_status,)
        )
        if LotStatus(lot.status) not in valid_sources:
            raise HTTPException(
                status_code=409,
                detail=f"Không thể ghi nhận {payload.event_type.value} khi lô ở trạng thái {lot.status}.",
            )
        lot.status = target_status.value

    event = _event(
        lot,
        principal,
        payload.event_type.value,
        payload.occurred_at,
        payload.public_note,
        payload.details,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.post("/derive", response_model=LotRead, status_code=status.HTTP_201_CREATED)
@require_permission("lots:write")
def derive_lot(
    payload: LotDeriveCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Lot:
    if payload.relation_type == "merge" and len(payload.source_allocations) < 2:
        raise HTTPException(status_code=422, detail="Merge cần ít nhất hai lô nguồn.")
    if payload.relation_type == "split" and len(payload.source_allocations) != 1:
        raise HTTPException(status_code=422, detail="Split cần đúng một lô nguồn.")
    if payload.quantity > sum(
        (allocation.quantity for allocation in payload.source_allocations), Decimal(0)
    ):
        raise HTTPException(
            status_code=422,
            detail="Sản lượng lô mới không thể vượt tổng nguyên liệu nguồn.",
        )

    source_ids = sorted(
        (allocation.lot_id for allocation in payload.source_allocations), key=str
    )
    sources = list(
        db.scalars(
            select(Lot)
            .where(
                Lot.id.in_(source_ids),
                Lot.organization_id == principal.organization_id,
            )
            .order_by(Lot.id)
            .with_for_update()
        ).all()
    )
    if len(sources) != len(source_ids):
        raise HTTPException(status_code=404, detail="Không tìm thấy đủ lô nguồn.")
    source_by_id = {lot.id: lot for lot in sources}
    used_rows = db.execute(
        select(LotLineage.source_lot_id, func.sum(LotLineage.source_quantity))
        .where(LotLineage.source_lot_id.in_(source_ids))
        .group_by(LotLineage.source_lot_id)
    ).all()
    already_allocated = {source_id: amount for source_id, amount in used_rows}

    for allocation in payload.source_allocations:
        source = source_by_id[allocation.lot_id]
        if source.status in {
            LotStatus.in_transit.value,
            LotStatus.sold.value,
            LotStatus.discarded.value,
        }:
            raise HTTPException(status_code=409, detail="Lô nguồn không còn khả dụng.")
        if source.unit.casefold() != payload.unit.casefold():
            raise HTTPException(
                status_code=422, detail="Đơn vị các lô phải thống nhất."
            )
        remaining = source.quantity - already_allocated.get(source.id, Decimal(0))
        if allocation.quantity > remaining:
            raise HTTPException(
                status_code=409,
                detail=f"Lô {source.lot_number or source.id} chỉ còn {remaining} {source.unit} khả dụng.",
            )

    get_tenant_record(db, Product, payload.product_id, principal)
    get_tenant_record(db, Farm, payload.origin_farm_id, principal)
    target = Lot(
        public_code=secrets.token_urlsafe(32),
        lot_number=payload.lot_number,
        organization_id=principal.organization_id,
        origin_organization_id=principal.organization_id,
        product_id=payload.product_id,
        origin_farm_id=payload.origin_farm_id,
        quantity=payload.quantity,
        unit=payload.unit.strip(),
        status=LotStatus.created.value,
        created_by_id=principal.user_id,
    )
    db.add(target)
    db.flush()
    for allocation in payload.source_allocations:
        db.add(
            LotLineage(
                organization_id=principal.organization_id,
                source_lot_id=allocation.lot_id,
                target_lot_id=target.id,
                relation_type=payload.relation_type,
                source_quantity=allocation.quantity,
                unit=payload.unit.strip(),
            )
        )
    db.add(
        _event(
            target,
            principal,
            "lot_created",
            datetime.now(UTC),
            payload.public_note,
            {"derived": True, "source_count": len(source_ids)},
        )
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Số lô đã tồn tại.") from error
    db.refresh(target)
    return target


@router.get("/{lot_id}/lineage", response_model=Page[LotLineageRead])
@require_permission("lots:read")
def list_lot_lineage(
    lot_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> Page[LotLineageRead]:
    lot = _get_lot(db, lot_id, principal)
    base = select(LotLineage).where(
        or_(LotLineage.source_lot_id == lot.id, LotLineage.target_lot_id == lot.id)
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    edges = db.scalars(
        base.order_by(LotLineage.created_at.desc(), LotLineage.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(items=list(edges), page=page, page_size=page_size, total=total)
