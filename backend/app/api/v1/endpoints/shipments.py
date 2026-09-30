from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import is_inspection_principal, require_permission
from app.core.database import get_db
from app.models.cold_chain import Shipment, TemperatureReading
from app.models.identity import Organization
from app.models.traceability import Lot, LotEvent
from app.schemas.traceability import (
    Page,
    ShipmentCreate,
    ShipmentRead,
    TemperatureReadingRead,
)

router = APIRouter()


@router.get("/", response_model=Page[ShipmentRead])
@require_permission("shipments:read")
def list_shipments(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
) -> Page[ShipmentRead]:
    base = select(Shipment)
    if not is_inspection_principal(principal):
        base = base.where(
            (Shipment.sender_organization_id == principal.organization_id)
            | (Shipment.receiver_organization_id == principal.organization_id)
        )
    if status_filter is not None:
        if status_filter not in {"in_transit", "received", "cancelled"}:
            raise HTTPException(
                status_code=422, detail="Trạng thái vận chuyển không hợp lệ."
            )
        base = base.where(Shipment.status == status_filter)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    shipments = db.scalars(
        base.order_by(Shipment.created_at.desc(), Shipment.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(items=list(shipments), page=page, page_size=page_size, total=total)


@router.post("/", response_model=ShipmentRead, status_code=status.HTTP_201_CREATED)
@require_permission("shipments:create")
def create_shipment(
    payload: ShipmentCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Shipment:
    if payload.shipped_at.tzinfo is None or payload.shipped_at.utcoffset() is None:
        raise HTTPException(status_code=422, detail="shipped_at phải có múi giờ.")
    if payload.receiver_organization_id == principal.organization_id:
        raise HTTPException(status_code=422, detail="Bên nhận phải là tổ chức khác.")
    receiver = db.get(Organization, payload.receiver_organization_id)
    if receiver is None or not receiver.is_active:
        raise HTTPException(status_code=404, detail="Không tìm thấy tổ chức nhận.")

    lot = db.scalar(
        select(Lot)
        .where(
            Lot.id == payload.lot_id,
            Lot.organization_id == principal.organization_id,
        )
        .with_for_update()
    )
    if lot is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lô thuộc tổ chức.")
    if lot.status not in {"packed", "stored", "received"}:
        raise HTTPException(status_code=409, detail="Lô chưa sẵn sàng để vận chuyển.")

    prior_status = lot.status
    lot.status = "in_transit"
    shipment = Shipment(
        lot_id=lot.id,
        organization_id=principal.organization_id,
        sender_organization_id=principal.organization_id,
        receiver_organization_id=receiver.id,
        status="in_transit",
        shipped_at=payload.shipped_at,
        created_by_id=principal.user_id,
    )
    db.add(shipment)
    db.flush()
    db.add(
        LotEvent(
            lot_id=lot.id,
            organization_id=lot.organization_id,
            actor_user_id=principal.user_id,
            event_type="shipped",
            occurred_at=payload.shipped_at,
            public_note=None,
            details={"shipment_id": str(shipment.id), "prior_status": prior_status},
        )
    )
    try:
        db.commit()
    except IntegrityError as error:
        # `uq_shipments_one_in_transit_per_lot` rejects a concurrent shipment
        # for the same lot; surface it as a conflict rather than a 500.
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Lô đã có chuyến vận chuyển đang diễn ra."
        ) from error
    db.refresh(shipment)
    return shipment


@router.get("/{shipment_id}", response_model=ShipmentRead)
@require_permission("shipments:read")
def get_shipment(
    shipment_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Shipment:
    statement = select(Shipment).where(Shipment.id == shipment_id)
    if not is_inspection_principal(principal):
        statement = statement.where(
            (Shipment.sender_organization_id == principal.organization_id)
            | (Shipment.receiver_organization_id == principal.organization_id)
        )
    shipment = db.scalar(statement)
    if shipment is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy chuyến vận chuyển.")
    return shipment


@router.get("/{shipment_id}/readings", response_model=Page[TemperatureReadingRead])
@require_permission("shipments:read")
def list_shipment_readings(
    shipment_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
) -> Page[TemperatureReadingRead]:
    shipment_statement = select(Shipment).where(Shipment.id == shipment_id)
    if not is_inspection_principal(principal):
        shipment_statement = shipment_statement.where(
            (Shipment.sender_organization_id == principal.organization_id)
            | (Shipment.receiver_organization_id == principal.organization_id)
        )
    if db.scalar(shipment_statement) is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy chuyến vận chuyển.")

    base = select(TemperatureReading).where(
        TemperatureReading.shipment_id == shipment_id
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    readings = db.scalars(
        base.order_by(TemperatureReading.measured_at.desc(), TemperatureReading.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(items=list(readings), page=page, page_size=page_size, total=total)


@router.post("/{shipment_id}/receive", response_model=ShipmentRead)
@require_permission("shipments:receive")
def receive_shipment(
    shipment_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Shipment:
    shipment = db.scalar(
        select(Shipment)
        .where(
            Shipment.id == shipment_id,
            Shipment.receiver_organization_id == principal.organization_id,
            Shipment.status == "in_transit",
        )
        .with_for_update()
    )
    if shipment is None:
        raise HTTPException(
            status_code=404, detail="Không tìm thấy chuyến đang chờ nhận."
        )

    lot = db.scalar(select(Lot).where(Lot.id == shipment.lot_id).with_for_update())
    if lot is None or lot.status != "in_transit":
        raise HTTPException(
            status_code=409, detail="Lô không còn ở trạng thái vận chuyển."
        )

    received_at = datetime.now(UTC)
    lot.organization_id = principal.organization_id
    lot.status = "received"
    db.flush()
    shipment.organization_id = principal.organization_id
    shipment.status = "received"
    shipment.received_at = received_at
    shipment.received_by_id = principal.user_id
    db.add(
        LotEvent(
            lot_id=lot.id,
            # Custody has already moved to the receiver above; anchor the event
            # to the lot's owning organization so the provenance history of a
            # lot never splits across two organizations.
            organization_id=lot.organization_id,
            actor_user_id=principal.user_id,
            event_type="received",
            occurred_at=received_at,
            public_note=None,
            details={"shipment_id": str(shipment.id)},
        )
    )
    db.commit()
    db.refresh(shipment)
    return shipment
