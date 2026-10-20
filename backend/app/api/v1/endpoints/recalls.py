"""API endpoints for managing recall orders, notifications, and confirmations (N3-49, N3-50, N3-52, N3-53, N3-55)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.schemas.recall import (
    RecallConfirmCreate,
    RecallCreate,
    RecallNotificationRead,
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
    "/notifications",
    response_model=list[RecallNotificationRead],
    summary="Thông báo lệnh thu hồi liên quan tới tổ chức hiện tại",
)
@require_permission("recalls:read")
def list_recall_notifications(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    include_completed: Annotated[bool, Query()] = False,
) -> list[RecallNotificationRead]:
    return recall_service.list_recall_notifications(
        db, principal, include_completed=include_completed
    )


@router.get(
    "/{recall_id}",
    response_model=RecallOrderRead,
    summary="Chi tiết lệnh thu hồi (kèm danh sách hậu duệ động và tiến độ xác nhận)",
)
@require_permission("recalls:read")
def get_recall_order(
    recall_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> RecallOrderRead:
    return recall_service.get_recall(db, principal, recall_id)


@router.post(
    "/{recall_id}/confirm",
    response_model=RecallOrderRead,
    summary="Tổ chức liên quan xác nhận đã xử lý phần lô ảnh hưởng của mình",
)
@router.post(
    "/{recall_id}/acknowledge",
    response_model=RecallOrderRead,
    include_in_schema=False,
)
@require_permission("recalls:confirm")
def confirm_recall_order_handling(
    recall_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    payload: RecallConfirmCreate | None = None,
) -> RecallOrderRead:
    effective_payload = payload or RecallConfirmCreate()
    return recall_service.confirm_recall_handling(
        db, principal, recall_id, effective_payload
    )


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
