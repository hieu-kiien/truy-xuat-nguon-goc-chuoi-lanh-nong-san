from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.models.handover import Handover
from app.models.identity import Organization
from app.schemas.handover import (
    HandoverCreate,
    HandoverDecisionRead,
    HandoverRead,
    HandoverReject,
    OrganizationOption,
)
from app.services import handover_service

router = APIRouter()


@router.get("/organizations", response_model=list[OrganizationOption])
@require_permission("handovers:create")
def list_organizations(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Organization]:
    return handover_service.list_transfer_organizations(db, principal)


@router.get("/incoming", response_model=list[HandoverRead])
@require_permission("handovers:resolve")
def list_incoming(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    return handover_service.list_handovers(db, principal, incoming=True)


@router.get("/outgoing", response_model=list[HandoverRead])
@require_permission("handovers:create")
def list_outgoing(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    return handover_service.list_handovers(db, principal, incoming=False)


@router.post("/", response_model=HandoverRead, status_code=status.HTTP_201_CREATED)
@require_permission("handovers:create")
def create_handover(
    payload: HandoverCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    return handover_service.create_handover(db, principal, payload)


@router.post("/{handover_id}/accept", response_model=HandoverDecisionRead)
@require_permission("handovers:resolve")
def accept_handover(
    handover_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Handover:
    return handover_service.accept_handover(db, principal, handover_id)


@router.post("/{handover_id}/reject", response_model=HandoverDecisionRead)
@require_permission("handovers:resolve")
def reject_handover(
    handover_id: UUID,
    payload: HandoverReject,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Handover:
    return handover_service.reject_handover(db, principal, handover_id, payload.reason)
