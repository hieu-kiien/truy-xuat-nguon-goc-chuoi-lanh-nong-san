from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.schemas.location import LocationCreate, LocationRead
from app.services import lot_lifecycle_service

router = APIRouter()


@router.get("/", response_model=list[LocationRead])
@require_permission("locations:manage")
def list_locations(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    return lot_lifecycle_service.list_locations(db, principal)


@router.post("/", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
@require_permission("locations:manage")
def create_location(
    payload: LocationCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    return lot_lifecycle_service.create_location(db, principal, payload)
