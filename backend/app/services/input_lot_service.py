"""Input material declarations for harvested lots (N3-38).

A grower records which input material was used for a lot, with the date and
the amount. Every declaration is written as one event on the lot chain, so the
record cannot be edited away. The catalogue of input materials is the shared
product catalogue, which only an administrator maintains.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.core.tenancy import get_tenant_record
from app.models.lot import Lot
from app.models.lot_input import LotInputLot
from app.models.product import Product
from app.schemas.lot import InputLotCreate, InputLotRead
from app.services import event_service

logger = logging.getLogger(__name__)

INPUT_LOT_EVENT_TYPE = "input_lot_declared"


def _product_names(db: Session, product_ids: list[UUID]) -> dict[UUID, str]:
    if not product_ids:
        return {}
    rows = db.execute(
        select(Product.id, Product.name).where(Product.id.in_(product_ids))
    ).all()
    return {row.id: row.name for row in rows}


def declare_input_lots(
    db: Session,
    principal: Principal,
    lot_id: UUID,
    payload: InputLotCreate,
) -> list[InputLotRead]:
    """Record the input materials used for a lot.

    The caller must hold the lot, the input materials must come from the
    shared catalogue, and the date may sit before or after the harvest.
    """
    lot = get_tenant_record(db, Lot, lot_id, principal)
    if lot.current_holder_organization_id != principal.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ tổ chức đang giữ lô mới được khai vật tư.",
        )

    product_ids = [item.product_id for item in payload.items]
    names = _product_names(db, product_ids)
    missing = [product_id for product_id in product_ids if product_id not in names]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Vật tư không có trong danh mục nông sản.",
        )

    declared: list[InputLotRead] = []
    for item in payload.items:
        record = LotInputLot(
            lot_id=lot.id,
            product_id=item.product_id,
            quantity=item.quantity,
            used_on=item.used_on,
            organization_id=principal.organization_id,
            created_by_user_id=principal.user_id,
            created_at=datetime.now(UTC),
        )
        db.add(record)
        db.flush()

        # Mỗi lần khai là một sự kiện trong chuỗi của lô (N3-38).
        event_service.append_event(
            db,
            principal,
            lot.id,
            event_type=INPUT_LOT_EVENT_TYPE,
            payload={
                "input_lot_id": str(record.id),
                "product_id": str(item.product_id),
                "product_name": names[item.product_id],
                "quantity": float(item.quantity),
                "used_on": item.used_on.isoformat(),
                "declared_by_organization_id": str(principal.organization_id),
            },
        )
        declared.append(
            InputLotRead(
                id=record.id,
                lot_id=record.lot_id,
                product_id=record.product_id,
                product_name=names[item.product_id],
                quantity=record.quantity,
                used_on=record.used_on,
                organization_id=record.organization_id,
                created_at=record.created_at,
            )
        )

    db.commit()
    return declared


def list_input_lots(
    db: Session, principal: Principal, lot_id: UUID
) -> list[InputLotRead]:
    """List the input material declarations of a lot.

    Row level security keeps the declarations inside the organization that
    made them, plus the inspectors who have to check the file.
    """
    get_tenant_record(db, Lot, lot_id, principal, allow_historical=True)
    rows = list(
        db.scalars(
            select(LotInputLot)
            .where(LotInputLot.lot_id == lot_id)
            .order_by(LotInputLot.used_on.asc(), LotInputLot.created_at.asc())
        ).all()
    )
    names = _product_names(db, [row.product_id for row in rows])
    return [
        InputLotRead(
            id=row.id,
            lot_id=row.lot_id,
            product_id=row.product_id,
            product_name=names.get(row.product_id, ""),
            quantity=row.quantity,
            used_on=row.used_on,
            organization_id=row.organization_id,
            created_at=row.created_at,
        )
        for row in rows
    ]
