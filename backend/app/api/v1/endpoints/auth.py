from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import enforce_route_permission, require_permission
from app.core.config import settings
from app.core.database import get_db, set_db_context
from app.core.demo import DEMO_EMAILS
from app.core.security import (
    hash_session_token,
    new_session_token,
    verify_dummy_password,
    verify_password,
)
from app.models.identity import AuthSession, Organization, Role, User
from app.schemas.auth import DemoLoginRequest, LoginRequest, SessionUser

router = APIRouter()
session_router = APIRouter(dependencies=[Depends(enforce_route_permission)])
AUTH_ERROR = "Email hoặc mật khẩu không đúng."
DEMO_AUTH_ERROR = "Tài khoản demo không khả dụng."
MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15


def _session_user(user: User, organization: Organization, role: Role) -> SessionUser:
    return SessionUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        organization_id=organization.id,
        organization_name=organization.name,
        organization_type=organization.organization_type,
        role=role.code,
    )


def _issue_session(
    user: User,
    response: Response,
    db: Session,
    *,
    now: datetime,
) -> SessionUser:
    set_db_context(db, login_organization_id=user.organization_id)
    organization = db.get(Organization, user.organization_id)
    role = db.get(Role, user.role_code)
    if organization is None or role is None or not organization.is_active:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=AUTH_ERROR)

    set_db_context(
        db,
        organization_id=user.organization_id,
        user_id=user.id,
        role=role.code,
    )
    token = new_session_token()
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            created_at=now,
            expires_at=now + timedelta(minutes=settings.SESSION_TTL_MINUTES),
        )
    )
    db.commit()

    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.SESSION_TTL_MINUTES * 60,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    response.headers["X-Session-Token"] = token
    return _session_user(user, organization, role)


@router.post("/login", response_model=SessionUser)
def login(
    payload: LoginRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> SessionUser:
    email = str(payload.email).strip().lower()
    set_db_context(db, login_email=email)
    user = db.scalar(select(User).where(User.email == email).with_for_update())
    if user is None:
        verify_dummy_password(payload.password)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=AUTH_ERROR)

    password_ok = verify_password(user.password_hash, payload.password)
    now = datetime.now(UTC)
    is_locked = user.locked_until is not None and user.locked_until > now

    if is_locked or not user.is_active or not password_ok:
        if user.locked_until is not None and user.locked_until <= now:
            user.failed_login_attempts = 0
            user.locked_until = None

        if not is_locked and user.is_active and not password_ok:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = now + timedelta(minutes=LOCK_MINUTES)

        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=AUTH_ERROR)

    user.failed_login_attempts = 0
    user.locked_until = None
    return _issue_session(user, response, db, now=now)


@router.post("/demo-login", response_model=SessionUser)
def demo_login(
    payload: DemoLoginRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> SessionUser:
    if not settings.demo_login_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=DEMO_AUTH_ERROR
        )

    email = str(payload.email).strip().lower()
    if email not in DEMO_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=DEMO_AUTH_ERROR
        )

    set_db_context(db, login_email=email)
    user = db.scalar(select(User).where(User.email == email).with_for_update())
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=DEMO_AUTH_ERROR
        )

    user.failed_login_attempts = 0
    user.locked_until = None
    return _issue_session(user, response, db, now=datetime.now(UTC))


@session_router.get("/me", response_model=SessionUser)
@require_permission("auth:session")
def get_session_user(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> SessionUser:
    return SessionUser(
        id=principal.user_id,
        email=principal.email,
        full_name=principal.full_name,
        organization_id=principal.organization_id,
        organization_name=principal.organization_name,
        organization_type=principal.organization_type,
        role=principal.role,
    )


@session_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("auth:session")
def logout(
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME) or request.headers.get(
        "X-Session-Token"
    )
    if token:
        auth_session = db.scalar(
            select(AuthSession).where(
                AuthSession.user_id == principal.user_id,
                AuthSession.token_hash == hash_session_token(token),
                AuthSession.revoked_at.is_(None),
            )
        )
        if auth_session is not None:
            auth_session.revoked_at = datetime.now(UTC)
            db.commit()
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
