"""API endpoints for the caller's own organization (N3-57, N3-30)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.schemas.organization import (
    ContactEmailUpdate,
    InvitationCreate,
    InvitationCreated,
    InvitationRead,
    MemberRead,
    OrganizationRead,
)
from app.services import invitation_service, organization_service

router = APIRouter()


@router.get(
    "/me",
    response_model=OrganizationRead,
    summary="Thông tin tổ chức của tôi (N3-57)",
)
@require_permission("organizations:read")
def read_my_organization(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> OrganizationRead:
    return organization_service.read_my_organization(db, principal)


@router.put(
    "/me/contact-email",
    response_model=OrganizationRead,
    summary="Đặt địa chỉ email đầu mối của tổ chức (N3-57, N3-30)",
)
@require_permission("organizations:manage")
def update_contact_email(
    payload: ContactEmailUpdate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> OrganizationRead:
    """Set the address that receives recall notices and member invitations."""
    return organization_service.update_contact_email(db, principal, payload)


@router.post(
    "/invitations",
    response_model=InvitationCreated,
    status_code=201,
    summary="Mời một thành viên mới vào tổ chức (N3-30)",
)
@require_permission("organizations:manage")
def create_invitation(
    payload: InvitationCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> InvitationCreated:
    """Send an invitation link that works once and expires after 72 hours."""
    return invitation_service.create_invitation(db, principal, payload)


@router.get(
    "/invitations",
    response_model=list[InvitationRead],
    summary="Danh sách lời mời của tổ chức (N3-30)",
)
@require_permission("organizations:manage")
def list_invitations(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> list[InvitationRead]:
    return invitation_service.list_invitations(db, principal)


@router.post(
    "/invitations/{invitation_id}/revoke",
    response_model=InvitationRead,
    summary="Thu hồi một lời mời (N3-30)",
)
@require_permission("organizations:manage")
def revoke_invitation(
    invitation_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> InvitationRead:
    return invitation_service.revoke_invitation(db, principal, invitation_id)


@router.get(
    "/members",
    response_model=list[MemberRead],
    summary="Danh sách thành viên của tổ chức (N3-30)",
)
@require_permission("organizations:read")
def list_members(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> list[MemberRead]:
    return invitation_service.list_members(db, principal)


@router.post(
    "/members/{user_id}/deactivate",
    response_model=MemberRead,
    summary="Vô hiệu hoá thành viên đã nghỉ (N3-30)",
)
@require_permission("organizations:manage")
def deactivate_member(
    user_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> MemberRead:
    """Disable the account of a member who left the organization."""
    return invitation_service.deactivate_member(db, principal, user_id)
