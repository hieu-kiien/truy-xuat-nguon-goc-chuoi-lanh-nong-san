"""API endpoints for managing recall orders (N3-49 & N3-53)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.schemas.recall import (
    RecallCreate,
    RecallOrderLotIncidentUpdate,
    RecallOrderRead,
)
from app.services import recall_service

router = APIRouter()


@router.post(
    "",
    response_model=RecallOrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Mở lệnh thu hồi cho lô có sự cố",
)
@router.post(
    "/",
    response_model=RecallOrderRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@require_permission("recalls:open")
def open_recall_order(
    payload: RecallCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> RecallOrderRead:
    return recall_service.open_recall(db, principal, payload)


@router.get(
    "",
    response_model=list[RecallOrderRead],
    summary="Danh sách lệnh thu hồi",
)
@router.get(
    "/",
    response_model=list[RecallOrderRead],
    include_in_schema=False,
)
@require_permission("recalls:read")
def list_recall_orders(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[str | None, Query(pattern="^(open|completed)$")] = None,
) -> list[RecallOrderRead]:
    return recall_service.list_recalls(db, principal, status_filter=status_filter)


@router.get(
    "/{recall_id}",
    response_model=RecallOrderRead,
    summary="Chi tiết lệnh thu hồi",
)
@require_permission("recalls:read")
def get_recall_order(
    recall_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> RecallOrderRead:
    return recall_service.get_recall(db, principal, recall_id)


@router.post(
    "/{recall_id}/complete",
    response_model=RecallOrderRead,
    summary="Hoàn tất lệnh thu hồi",
)
@require_permission("recalls:manage")
def complete_recall_order(
    recall_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> RecallOrderRead:
    return recall_service.complete_recall_order(db, principal, recall_id)


@router.patch(
    "/{recall_id}/lots/{lot_id}",
    response_model=RecallOrderRead,
    summary="Cập nhật cờ sự cố của lô trong lệnh thu hồi",
)
@require_permission("recalls:manage")
def update_lot_incident_flag(
    recall_id: UUID,
    lot_id: UUID,
    payload: RecallOrderLotIncidentUpdate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> RecallOrderRead:
    recall_service.update_incident_flag(
        db, principal, recall_id, lot_id, payload.incident_flag
    )
    return recall_service.get_recall(db, principal, recall_id)
