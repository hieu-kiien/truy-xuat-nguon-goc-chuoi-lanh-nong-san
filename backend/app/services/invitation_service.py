"""Organization member invitations (N3-30).

An administrator invites a colleague by e-mail. The link carries a token that
works once and expires after 72 hours; the recipient sets a password and joins
the inviting organization with the chosen role. An administrator can also
deactivate a member who has left.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.core.security import hash_password
from app.models.identity import Organization, Role, User
from app.models.organization_invitation import (
    INVITATION_TTL_HOURS,
    OrganizationInvitation,
)
from app.schemas.organization import (
    InvitationCreate,
    InvitationRead,
    MemberRead,
)
from app.services import email_service

MIN_PASSWORD_LENGTH = 12


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _assert_role_known(db: Session, role_code: str) -> Role:
    role = db.get(Role, role_code)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Vai trò '{role_code}' không tồn tại.",
        )
    return role


def create_invitation(
    db: Session, principal: Principal, payload: InvitationCreate
) -> InvitationRead:
    """Create one invitation and send the e-mail with the single-use link."""
    email = payload.email.strip().lower()
    _assert_role_known(db, payload.role_code)

    if payload.role_code == "system_admin" and principal.role != "system_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ quản trị hệ thống mới được gán vai trò quản trị hệ thống.",
        )

    existing_user = db.scalar(select(User.id).where(User.email == email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Địa chỉ email này đã có tài khoản.",
        )

    pending = db.scalar(
        select(OrganizationInvitation.id).where(
            OrganizationInvitation.organization_id == principal.organization_id,
            OrganizationInvitation.email == email,
            OrganizationInvitation.accepted_at.is_(None),
            OrganizationInvitation.revoked_at.is_(None),
        )
    )
    if pending is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Đã có lời mời đang chờ cho địa chỉ này.",
        )

    organization = db.get(Organization, principal.organization_id)
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    invitation = OrganizationInvitation(
        organization_id=principal.organization_id,
        email=email,
        role_code=payload.role_code,
        token_hash=_token_hash(token),
        invited_by_user_id=principal.user_id,
        created_at=now,
        expires_at=now + timedelta(hours=INVITATION_TTL_HOURS),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    invitation_url = f"{email_service.settings.PUBLIC_APP_URL.rstrip('/')}/moi-dai-nhiep?token={token}"
    email_service.deliver_email(
        db,
        recipient_email=email,
        subject=f"[{organization.name}] Lời mời tham gia tổ chức",
        body=email_service.invitation_body(
            organization.name, principal.full_name, invitation_url
        ),
        kind=email_service.ORGANIZATION_INVITATION_KIND,
        organization_id=principal.organization_id,
        related_id=str(invitation.id),
    )
    return _serialize(invitation, organization.name)


def _serialize(
    invitation: OrganizationInvitation, organization_name: str
) -> InvitationRead:
    status_value = "pending"
    if invitation.accepted_at is not None:
        status_value = "accepted"
    elif invitation.revoked_at is not None:
        status_value = "revoked"
    elif invitation.expires_at <= datetime.now(UTC):
        status_value = "expired"
    return InvitationRead(
        id=invitation.id,
        organization_id=invitation.organization_id,
        organization_name=organization_name,
        email=invitation.email,
        role_code=invitation.role_code,
        status=status_value,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        revoked_at=invitation.revoked_at,
    )


def list_invitations(db: Session, principal: Principal) -> list[InvitationRead]:
    """List the invitations of the caller's organization."""
    organization = db.get(Organization, principal.organization_id)
    rows = list(
        db.scalars(
            select(OrganizationInvitation)
            .where(OrganizationInvitation.organization_id == principal.organization_id)
            .order_by(OrganizationInvitation.created_at.desc())
        ).all()
    )
    name = organization.name if organization else ""
    return [_serialize(row, name) for row in rows]


def revoke_invitation(
    db: Session, principal: Principal, invitation_id: UUID
) -> InvitationRead:
    """Withdraw an invitation that has not been accepted yet."""
    invitation = db.scalar(
        select(OrganizationInvitation).where(
            OrganizationInvitation.id == invitation_id,
            OrganizationInvitation.organization_id == principal.organization_id,
        )
    )
    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lời mời.",
        )
    if invitation.accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lời mời đã được chấp nhận thì không thể thu hồi.",
        )
    if invitation.revoked_at is None:
        invitation.revoked_at = datetime.now(UTC)
        db.commit()
        db.refresh(invitation)
    organization = db.get(Organization, principal.organization_id)
    return _serialize(invitation, organization.name if organization else "")


def read_invitation_by_token(db: Session, token: str) -> dict:
    """Return the public details of an invitation, without touching the token.

    The read happens inside a database function because the caller has no
    session, and the row level security of the table only opens up for the
    organization that sent the invitation.
    """
    row = db.execute(
        text(
            "SELECT invitation_organization_id, invitation_organization_name, "
            "invitation_email, invitation_role_code, invitation_expires_at, "
            "invitation_accepted_at, invitation_revoked_at "
            "FROM public.app_read_invitation(:token_hash)"
        ),
        {"token_hash": _token_hash(token)},
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lời mời không tồn tại.",
        )
    if row.invitation_accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Lời mời này đã được sử dụng.",
        )
    if row.invitation_revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Lời mời này đã bị thu hồi.",
        )
    expires_at = row.invitation_expires_at
    if expires_at is not None and expires_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Lời mời này đã hết hạn.",
        )
    organization = db.get(Organization, row.invitation_organization_id)
    return {
        "email": row.invitation_email,
        "organization_id": str(row.invitation_organization_id),
        "organization_name": row.invitation_organization_name
        or (organization.name if organization else ""),
        "role_code": row.invitation_role_code,
        "expires_at": expires_at.isoformat() if expires_at else "",
    }


def accept_invitation(
    db: Session, *, token: str, password: str, full_name: str
) -> dict:
    """Create the member account from an invitation.

    The write happens inside the database function so the application role
    never needs to create accounts of other organizations.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Mật khẩu phải có ít nhất {MIN_PASSWORD_LENGTH} ký tự.",
        )
    if not full_name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cần nhập họ tên.",
        )

    try:
        row = db.execute(
            text(
                "SELECT accepted_user_id, accepted_organization_id, "
                "accepted_role_code, accepted_email "
                "FROM public.app_accept_invitation(:token_hash, :password_hash, :full_name)"
            ),
            {
                "token_hash": _token_hash(token),
                "password_hash": hash_password(password),
                "full_name": full_name.strip(),
            },
        ).first()
    except ProgrammingError as error:
        message = str(error.orig) if getattr(error, "orig", None) else str(error)
        if "expired" in message:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Lời mời không tồn tại hoặc đã hết hạn.",
            ) from error
        if "already has an account" in message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Địa chỉ email này đã có tài khoản.",
            ) from error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể chấp nhận lời mời.",
        ) from error

    db.commit()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể chấp nhận lời mời.",
        )
    return {
        "user_id": str(row.accepted_user_id),
        "organization_id": str(row.accepted_organization_id),
        "role_code": row.accepted_role_code,
        "email": row.accepted_email,
    }


def list_members(db: Session, principal: Principal) -> list[MemberRead]:
    """List the members of the caller's organization."""
    rows = list(
        db.scalars(
            select(User)
            .where(User.organization_id == principal.organization_id)
            .order_by(User.full_name.asc(), User.email.asc())
        ).all()
    )
    return [
        MemberRead(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role_code=user.role_code,
            is_active=user.is_active,
            locked_until=user.locked_until,
        )
        for user in rows
    ]


def deactivate_member(db: Session, principal: Principal, user_id: UUID) -> MemberRead:
    """Deactivate a member who has left the organization."""
    try:
        db.execute(
            text("SELECT public.app_deactivate_member(:user_id)"), {"user_id": user_id}
        )
    except ProgrammingError as error:
        message = str(error.orig) if getattr(error, "orig", None) else str(error)
        if "Unknown member" in message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy thành viên.",
            ) from error
        if "another organization" in message:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Thành viên thuộc tổ chức khác.",
            ) from error
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ quản trị tổ chức mới được vô hiệu hoá thành viên.",
        ) from error
    db.commit()

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thành viên.",
        )
    return MemberRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role_code=user.role_code,
        is_active=user.is_active,
        locked_until=user.locked_until,
    )
