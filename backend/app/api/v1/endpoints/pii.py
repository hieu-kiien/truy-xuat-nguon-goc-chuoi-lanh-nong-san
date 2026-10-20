from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.schemas.pii import (
    PiiAnonymizationRequestCreate,
    PiiAnonymizationRequestRead,
)
from app.services import pii_service

router = APIRouter()


@router.post(
    "/anonymization-requests",
    response_model=PiiAnonymizationRequestRead,
    status_code=status.HTTP_201_CREATED,
)
@require_permission("pii:request")
def create_anonymization_request(
    payload: PiiAnonymizationRequestCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> PiiAnonymizationRequestRead:
    """Ask for the identifying data of a growing area to be erased."""
    request = pii_service.request_anonymization(
        db, principal, payload.farm_id, payload.reason
    )
    return PiiAnonymizationRequestRead.model_validate(request)


@router.get("/anonymization-requests", response_model=list[PiiAnonymizationRequestRead])
@require_permission("pii:request")
def list_anonymization_requests(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[PiiAnonymizationRequestRead]:
    """List the privacy requests the caller may see."""
    requests = pii_service.list_anonymization_requests(db, principal, limit=limit)
    return [PiiAnonymizationRequestRead.model_validate(item) for item in requests]


@router.post(
    "/anonymization-requests/{request_id}/execute",
    response_model=PiiAnonymizationRequestRead,
)
@require_permission("pii:anonymize")
def execute_anonymization_request(
    request_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> PiiAnonymizationRequestRead:
    """Erase the identifying data of the organization that asked for it."""
    request = pii_service.execute_anonymization(db, principal, request_id)
    return PiiAnonymizationRequestRead.model_validate(request)
