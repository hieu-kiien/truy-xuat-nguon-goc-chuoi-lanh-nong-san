from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.core.tenancy import get_tenant_record, tenant_select
from app.models.farm import Farm
from app.schemas.farm import FarmCreate, FarmRead, FarmUpdate

router = APIRouter()


@router.get("/", response_model=list[FarmRead])
@require_permission("farms:read")
def list_farms(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Farm]:
    return list(db.scalars(tenant_select(Farm, principal)).all())


@router.post("/", response_model=FarmRead, status_code=status.HTTP_201_CREATED)
@require_permission("farms:write")
def create_farm(
    payload: FarmCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Farm:
    farm = Farm(
        organization_id=principal.organization_id,
        name=payload.name,
        area_ha=payload.area_ha,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@router.get("/{farm_id}", response_model=FarmRead)
@require_permission("farms:read")
def get_farm(
    farm_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Farm:
    return get_tenant_record(db, Farm, farm_id, principal)


@router.put("/{farm_id}", response_model=FarmRead)
@require_permission("farms:write")
def update_farm(
    farm_id: UUID,
    payload: FarmUpdate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Farm:
    farm = get_tenant_record(db, Farm, farm_id, principal)
    farm.name = payload.name
    farm.area_ha = payload.area_ha
    farm.latitude = payload.latitude
    farm.longitude = payload.longitude
    db.commit()
    db.refresh(farm)
    return farm
