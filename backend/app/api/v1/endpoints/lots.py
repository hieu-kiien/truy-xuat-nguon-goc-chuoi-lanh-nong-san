from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.core.tenancy import get_tenant_record, tenant_select
from app.models.lot import Lot
from app.schemas.lot import LotCreate, LotRead
from app.services import lot_service

router = APIRouter()


@router.post("/", response_model=LotRead, status_code=status.HTTP_201_CREATED)
@require_permission("lots:create")
def create_lot(
    payload: LotCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Lot:
    return lot_service.create_harvest_lot(db, principal, payload)


@router.get("/", response_model=list[LotRead])
@require_permission("lots:read")
def list_lots(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Lot]:
    return list(db.scalars(tenant_select(Lot, principal)).all())


@router.get("/{lot_id}", response_model=LotRead)
@require_permission("lots:read")
def get_lot(
    lot_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Lot:
    return get_tenant_record(db, Lot, lot_id, principal)
