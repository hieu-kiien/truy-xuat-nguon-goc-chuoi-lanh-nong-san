"""API endpoints for the shared processing step catalogue (N3-27)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.schemas.processing import ProcessingStepCreate, ProcessingStepRead
from app.services import processing_step_service

router = APIRouter()


@router.get(
    "/",
    response_model=list[ProcessingStepRead],
    summary="Danh mục công đoạn chế biến (N3-27)",
)
@require_permission("processing_steps:read")
def list_processing_step_catalogue(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ProcessingStepRead]:
    """The processing steps a cooperative can record."""
    return processing_step_service.list_catalogue(db, principal)


@router.post(
    "/",
    response_model=ProcessingStepRead,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm một công đoạn chế biến vào danh mục (N3-27)",
)
@require_permission("processing_steps:manage")
def create_processing_step(
    payload: ProcessingStepCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> ProcessingStepRead:
    """Only an administrator maintains the shared catalogue."""
    return processing_step_service.create_catalogue_entry(db, principal, payload)
