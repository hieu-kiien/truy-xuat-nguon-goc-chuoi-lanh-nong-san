from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.core.lot_codes import generate_lot_code
from app.core.tenancy import get_tenant_record, tenant_select
from app.models.farm import Farm
from app.models.lot import Lot
from app.models.product import Product
from app.schemas.lot import LotCreate
from app.services import event_service


def create_harvest_lot(
    db: Session,
    principal: Principal,
    lot_in: LotCreate,
) -> Lot:
    farm = get_tenant_record(db, Farm, lot_in.farm_id, principal)
    product = db.scalar(select(Product).where(Product.id == lot_in.product_id))
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy sản phẩm trong danh mục.",
        )

    lot_code = generate_lot_code()
    lot = Lot(
        organization_id=principal.organization_id,
        farm_id=farm.id,
        name=product.name,
        lot_code=lot_code,
        product_id=product.id,
        harvested_on=lot_in.harvested_on,
        quantity=lot_in.quantity,
    )
    db.add(lot)

    try:
        db.flush()
        event_service.append_event(
            db,
            principal,
            lot.id,
            event_type="harvest_recorded",
            payload={
                "lot_code": lot_code,
                "product_id": str(product.id),
                "product_name": product.name,
                "harvested_on": lot_in.harvested_on.isoformat(),
                "quantity": format(lot_in.quantity, "f"),
                "unit": product.unit,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(lot)
    return lot


def list_lots(
    db: Session,
    principal: Principal,
    *,
    query: str | None,
    product_id: UUID | None,
    page: int,
    page_size: int,
    offset: int | None = None,
) -> list[Lot]:
    statement = tenant_select(Lot, principal)
    if query:
        escaped_query = (
            query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        search = f"%{escaped_query}%"
        statement = statement.where(
            or_(
                Lot.lot_code.ilike(search, escape="\\"),
                Lot.name.ilike(search, escape="\\"),
            )
        )
    if product_id:
        statement = statement.where(Lot.product_id == product_id)
    statement = (
        statement.order_by(Lot.harvested_on.desc().nulls_last(), Lot.id.desc())
        .offset(offset if offset is not None else (page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(statement).all())
