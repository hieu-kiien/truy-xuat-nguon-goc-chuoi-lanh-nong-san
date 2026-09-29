from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_session_token
from app.models.identity import AuthSession, Organization, Role, User


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    email: str
    full_name: str
    organization_id: UUID
    organization_name: str
    organization_type: str
    role: str


def get_current_principal(
    request: Request, db: Annotated[Session, Depends(get_db)]
) -> Principal:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Cần đăng nhập."
        )

    result = db.execute(
        select(AuthSession, User, Organization, Role)
        .join(User, AuthSession.user_id == User.id)
        .join(Organization, User.organization_id == Organization.id)
        .join(Role, User.role_code == Role.code)
        .where(
            AuthSession.token_hash == hash_session_token(token),
            AuthSession.revoked_at.is_(None),
            User.is_active.is_(True),
            Organization.is_active.is_(True),
        )
    ).first()

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập không hợp lệ.",
        )

    auth_session, user, organization, role = result
    now = datetime.now(UTC)
    if auth_session.expires_at <= now:
        db.delete(auth_session)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập đã hết hạn.",
        )

    db.info["organization_id"] = str(user.organization_id)
    db.execute(
        select(
            func.set_config(
                "app.current_organization", str(user.organization_id), True
            )
        )
    )

    return Principal(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        organization_id=user.organization_id,
        organization_name=organization.name,
        organization_type=organization.organization_type,
        role=role.code,
    )
