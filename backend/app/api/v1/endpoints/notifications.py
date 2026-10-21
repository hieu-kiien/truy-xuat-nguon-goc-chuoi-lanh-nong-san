"""API endpoints for the in-app notification centre (N3-56)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.schemas.notification import NotificationListRead, NotificationRead
from app.services import notification_service

router = APIRouter()


@router.get(
    "",
    response_model=NotificationListRead,
    summary="Danh sách thông báo của tôi kèm số chưa đọc (N3-56)",
)
@require_permission("notifications:read")
def list_notifications(
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> NotificationListRead:
    """Pending handovers, related recalls and cold chain violations."""
    return notification_service.list_notifications(db, principal, limit=limit)


@router.post(
    "/read-all",
    summary="Đánh dấu toàn bộ thông báo đã đọc (N3-56)",
)
@require_permission("notifications:read")
def mark_all_notifications_read(
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> dict:
    updated = notification_service.mark_all_read(db, principal)
    return {"updated": updated}


@router.post(
    "/{notification_id}/read",
    response_model=NotificationRead,
    status_code=status.HTTP_200_OK,
    summary="Đánh dấu một thông báo đã đọc (N3-56)",
)
@require_permission("notifications:read")
def mark_notification_read(
    notification_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> NotificationRead:
    return notification_service.mark_read(db, principal, notification_id)
