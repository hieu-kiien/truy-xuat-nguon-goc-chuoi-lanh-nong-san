from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    hash_session_token,
    new_session_token,
    verify_dummy_password,
    verify_password,
)
from app.core.security_events import log_security_event
from app.models.identity import AuthSession, Organization, Role, User
from app.schemas.auth import LoginRequest, SessionUser

router = APIRouter()

# A single message is returned for every failure mode (unknown email, wrong
# password, inactive account, locked account) so the endpoint cannot be used to
# enumerate which emails are registered.
AUTH_ERROR = "Email hoặc mật khẩu không đúng."


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


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.SESSION_TTL_MINUTES * 60,
        # The raw session token must never be readable by JavaScript.
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        path="/",
    )


@router.post("/login", response_model=SessionUser)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> SessionUser:
    email = str(payload.email).strip().casefold()
    db.info["login_email"] = email
    db.execute(select(func.set_config("app.login_email", email, True)))

    # Row lock serialises concurrent attempts for the same account so
    # `failed_login_attempts` cannot be lost to a read-modify-write race.
    user = db.scalar(select(User).where(User.email == email).with_for_update())
    if user is None:
        # Spend comparable CPU so an unknown email is not distinguishable by
        # response time from a known one.
        verify_dummy_password(payload.password)
        log_security_event(
            "auth.login_failed",
            request=request,
            email=email,
            reason="unknown_account",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=AUTH_ERROR)

    password_ok = verify_password(user.password_hash, payload.password)
    now = datetime.now(UTC)
    is_locked = user.locked_until is not None and user.locked_until > now

    if is_locked or not user.is_active or not password_ok:
        if user.locked_until is not None and user.locked_until <= now:
            # The lockout window elapsed: clear the counters so the next correct
            # password is accepted.
            user.failed_login_attempts = 0
            user.locked_until = None

        if is_locked:
            reason = "account_locked"
        elif not user.is_active:
            reason = "account_inactive"
        else:
            reason = "bad_password"
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
                user.locked_until = now + timedelta(
                    minutes=settings.ACCOUNT_LOCK_MINUTES
                )
                reason = "account_locked"

        # Read the audit fields *before* committing: once the transaction ends
        # the row-level-security context is gone, and touching a mapped
        # attribute afterwards would trigger a refresh that RLS may refuse.
        audit = {
            "user_id": str(user.id),
            "organization_id": str(user.organization_id),
            "failed_login_attempts": user.failed_login_attempts,
            "locked_until": user.locked_until.isoformat()
            if user.locked_until
            else None,
        }
        db.commit()
        log_security_event(
            "auth.login_failed",
            request=request,
            email=email,
            reason=reason,
            **audit,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=AUTH_ERROR)

    user.failed_login_attempts = 0
    user.locked_until = None
    organization = db.get(Organization, user.organization_id)
    role = db.get(Role, user.role_code)
    if organization is None or role is None or not organization.is_active:
        db.rollback()
        log_security_event(
            "auth.login_failed",
            request=request,
            email=email,
            user_id=str(user.id),
            reason="organization_unavailable",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=AUTH_ERROR)

    db.info.update(
        organization_id=str(user.organization_id),
        user_id=str(user.id),
        role=role.code,
    )
    for setting_name, setting_value in (
        ("app.current_organization", user.organization_id),
        ("app.current_user_id", user.id),
        ("app.current_role", role.code),
    ):
        db.execute(select(func.set_config(setting_name, str(setting_value), True)))

    # A brand new opaque token is minted on every successful login, so a token
    # observed before login (session fixation) is never promoted to an
    # authenticated one. Only its SHA-256 digest is persisted.
    token = new_session_token()
    expires_at = now + timedelta(minutes=settings.SESSION_TTL_MINUTES)
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            created_at=now,
            expires_at=expires_at,
        )
    )
    db.commit()

    _set_session_cookie(response, token)
    log_security_event(
        "auth.login_succeeded",
        level=20,
        request=request,
        user_id=str(user.id),
        organization_id=str(user.organization_id),
        email=email,
        role=role.code,
        expires_at=expires_at.isoformat(),
    )
    return _session_user(user, organization, role)


@router.get("/me", response_model=SessionUser)
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


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
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
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        path="/",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    log_security_event(
        "auth.logout",
        level=20,
        request=request,
        user_id=str(principal.user_id),
        organization_id=str(principal.organization_id),
    )
    return response
