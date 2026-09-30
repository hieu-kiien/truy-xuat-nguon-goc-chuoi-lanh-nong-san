from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.core.tenancy import get_tenant_record, tenant_select
from app.models.farm import Farm
from app.schemas.farm import FarmCreate, FarmPatch, FarmRead, FarmUpdate

router = APIRouter()


@router.get("/", response_model=list[FarmRead])
@require_permission("farms:read")
def list_farms(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Farm]:
    statement = (
        tenant_select(Farm, principal)
        .order_by(Farm.name, Farm.id)
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


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


@router.patch("/{farm_id}", response_model=FarmRead)
@require_permission("farms:write")
def patch_farm(
    farm_id: UUID,
    payload: FarmPatch,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Farm:
    farm = get_tenant_record(db, Farm, farm_id, principal)
    # `exclude_unset` keeps untouched columns intact; `id` and
    # `organization_id` are not part of the payload, so a rename leaves the
    # farm's identity — and every lot relation pointing at it — unchanged.
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(farm, field, value)
    db.commit()
    db.refresh(farm)
    return farm


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
