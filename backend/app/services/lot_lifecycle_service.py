"""Serialize internal custody operations and their immutable audit events."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.models.location import Location
from app.models.lot import Lot
from app.schemas.location import LocationCreate, LotConsume, LotMove
from app.services import event_service


def require_distribution(principal: Principal) -> None:
    if (
        principal.role not in {"distributor", "organization_admin"}
        or principal.organization_type != "distribution"
    ):
        raise HTTPException(
            403,
            "Chỉ nhà phân phối hoặc quản trị của tổ chức phân phối được thực hiện thao tác này.",
        )


def list_locations(db: Session, principal: Principal) -> list[Location]:
    require_distribution(principal)
    return list(
        db.scalars(
            select(Location)
            .where(Location.organization_id == principal.organization_id)
            .order_by(Location.name, Location.id)
        ).all()
    )


def create_location(
    db: Session, principal: Principal, payload: LocationCreate
) -> Location:
    require_distribution(principal)
    location = Location(
        organization_id=principal.organization_id, **payload.model_dump()
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def validate_locations(
    db: Session, principal: Principal, ids: set[UUID]
) -> dict[UUID, Location]:
    if not ids:
        return {}
    require_distribution(principal)
    locations = list(
        db.scalars(
            select(Location).where(
                Location.id.in_(ids),
                Location.organization_id == principal.organization_id,
            )
        ).all()
    )
    if len(locations) != len(ids):
        raise HTTPException(403, "Địa điểm phải thuộc tổ chức đang giữ lô.")
    return {location.id: location for location in locations}


def _lock_active(db: Session, principal: Principal, lot_id: UUID) -> Lot:
    require_distribution(principal)
    lot = db.scalar(
        select(Lot)
        .where(
            Lot.id == lot_id,
            Lot.current_holder_organization_id == principal.organization_id,
        )
        .with_for_update(of=Lot)
        .execution_options(populate_existing=True)
    )
    if lot is None:
        raise HTTPException(403, "Chỉ tổ chức đang giữ lô được thực hiện thao tác này.")
    if lot.status != "active":
        raise HTTPException(409, "Lô phải đang hoạt động và không chờ bàn giao.")
    return lot


def move_lot(db: Session, principal: Principal, lot_id: UUID, payload: LotMove) -> Lot:
    try:
        lot = _lock_active(db, principal, lot_id)
        location = validate_locations(db, principal, {payload.location_id})[
            payload.location_id
        ]
        if lot.current_location_id == location.id:
            raise HTTPException(409, "Lô đã ở địa điểm này.")
        event_service.append_event(
            db,
            principal,
            lot.id,
            event_type="lot_moved",
            payload={
                "from_location_id": str(lot.current_location_id)
                if lot.current_location_id
                else None,
                "to_location_id": str(location.id),
                "location_name": location.name,
                "location_address": location.address,
                "note": payload.note,
            },
        )
        lot.current_location_id = location.id
        db.commit()
        db.refresh(lot)
        return lot
    except Exception:
        db.rollback()
        raise


def consume_lot(
    db: Session, principal: Principal, lot_id: UUID, payload: LotConsume
) -> Lot:
    try:
        lot = _lock_active(db, principal, lot_id)
        # Append before terminal transition; the DB rejects further events afterwards.
        event_service.append_event(
            db,
            principal,
            lot.id,
            event_type="lot_consumed",
            payload={
                "quantity": format(lot.remaining_quantity, "f"),
                "location_id": str(lot.current_location_id)
                if lot.current_location_id
                else None,
                "note": payload.note,
            },
        )
        lot.remaining_quantity = 0
        lot.status = "consumed"
        db.commit()
        db.refresh(lot)
        return lot
    except Exception:
        db.rollback()
        raise
