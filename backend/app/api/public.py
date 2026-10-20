"""Trang truy xuất công khai — không yêu cầu đăng nhập (S-48, S-49, S-50)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.organization import (
    InvitationAccept,
    InvitationAccepted,
    InvitationPreview,
)
from app.services import invitation_service, public_trace_limiter, public_trace_service

router = APIRouter()

_RATE_LIMIT_DETAIL = (
    "Bạn tra cứu quá nhiều mã lô trong thời gian ngắn. Vui lòng thử lại sau ít phút."
)


@router.get("/trace/{lot_code}")
def get_public_trace(
    lot_code: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    client_ip = request.client.host if request.client else "unknown"
    normalized = (lot_code or "").strip().upper()

    # Đếm mọi lượt gọi, kể cả mã không tồn tại (S-50).
    if public_trace_limiter.is_over_limit(client_ip, normalized):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=_RATE_LIMIT_DETAIL,
            headers={"Retry-After": str(settings.PUBLIC_TRACE_RATE_WINDOW_SECONDS)},
        )

    return public_trace_service.trace_lot_code(db, normalized)


@router.get(
    "/invitations/{token}",
    response_model=InvitationPreview,
    summary="Xem lời mời tham gia tổ chức (N3-30)",
)
def get_public_invitation(
    token: str,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Public details of one invitation, so the invited person can accept it."""
    return invitation_service.read_invitation_by_token(db, token)


@router.post(
    "/invitations/{token}/accept",
    response_model=InvitationAccepted,
    summary="Chấp nhận lời mời và đặt mật khẩu (N3-30)",
)
def accept_public_invitation(
    token: str,
    payload: InvitationAccept,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Set the password and join the organization that sent the invitation."""
    return invitation_service.accept_invitation(
        db,
        token=token,
        password=payload.password,
        full_name=payload.full_name,
    )
