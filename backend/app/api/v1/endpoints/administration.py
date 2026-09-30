from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.core.security import hash_password
from app.models.identity import Organization, Role, User
from app.schemas.traceability import (
    OrganizationCreate,
    OrganizationProvisioned,
    OrganizationRead,
    Page,
    UserActiveUpdate,
    UserCreate,
    UserRead,
)

router = APIRouter()
ORGANIZATION_ROLE = {
    "farm": "grower",
    "cooperative": "cooperative",
    "transport": "transporter",
    "distribution": "distributor",
    "inspection": "inspector",
    "administration": "organization_admin",
}
VALID_ORGANIZATION_TYPES = set(ORGANIZATION_ROLE)


@router.get("/organizations", response_model=Page[OrganizationRead])
@require_permission("organizations:manage")
def list_organizations(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> Page[OrganizationRead]:
    base = select(Organization)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    organizations = db.scalars(
        base.order_by(Organization.name, Organization.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(items=list(organizations), page=page, page_size=page_size, total=total)


@router.post(
    "/organizations",
    response_model=OrganizationProvisioned,
    status_code=status.HTTP_201_CREATED,
)
@require_permission("organizations:manage")
def create_organization(
    payload: OrganizationCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> OrganizationProvisioned:
    if payload.organization_type not in VALID_ORGANIZATION_TYPES:
        raise HTTPException(status_code=422, detail="Loại tổ chức không hợp lệ.")

    organization = Organization(
        name=payload.name.strip(),
        organization_type=payload.organization_type,
        is_active=True,
    )
    db.add(organization)
    db.flush()
    db.execute(
        select(
            func.set_config("app.provisioning_organization", str(organization.id), True)
        )
    )
    email = str(payload.admin_email).strip().casefold()
    admin = User(
        organization_id=organization.id,
        role_code="organization_admin",
        email=email,
        full_name=payload.admin_full_name.strip(),
        password_hash=hash_password(payload.admin_password),
        failed_login_attempts=0,
        is_active=True,
    )
    db.add(admin)
    try:
        db.flush()
        response = OrganizationProvisioned(
            id=organization.id,
            name=organization.name,
            organization_type=organization.organization_type,
            is_active=organization.is_active,
            admin_user=UserRead(
                id=admin.id,
                organization_id=admin.organization_id,
                role_code=admin.role_code,
                email=admin.email,
                full_name=admin.full_name,
                is_active=admin.is_active,
            ),
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email đã được một tài khoản khác sử dụng.",
        ) from error
    return response


@router.get("/users", response_model=Page[UserRead])
@require_permission("users:manage")
def list_users(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> Page[UserRead]:
    base = select(User).where(User.organization_id == principal.organization_id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    users = db.scalars(
        base.order_by(User.full_name, User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(items=list(users), page=page, page_size=page_size, total=total)


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@require_permission("users:manage")
def create_user(
    payload: UserCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    email = str(payload.email).strip().casefold()
    role = db.get(Role, payload.role_code)
    if role is None:
        raise HTTPException(status_code=422, detail="Vai trò không hợp lệ.")
    if principal.role != "system_admin":
        allowed_role = ORGANIZATION_ROLE.get(principal.organization_type)
        if payload.role_code != allowed_role:
            raise HTTPException(
                status_code=403,
                detail="Quản trị tổ chức chỉ có thể tạo tài khoản theo loại tổ chức của mình.",
            )

    user = User(
        organization_id=principal.organization_id,
        role_code=payload.role_code,
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        failed_login_attempts=0,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Email đã được một tài khoản khác sử dụng."
        ) from error
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/active", response_model=UserRead)
@require_permission("users:manage")
def update_user_active(
    user_id: UUID,
    payload: UserActiveUpdate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if user_id == principal.user_id and not payload.is_active:
        raise HTTPException(
            status_code=409, detail="Không thể tự khóa tài khoản đang dùng."
        )
    user = db.scalar(
        select(User)
        .where(
            User.id == user_id,
            User.organization_id == principal.organization_id,
        )
        .with_for_update()
    )
    if user is None:
        raise HTTPException(
            status_code=404, detail="Không tìm thấy tài khoản trong tổ chức."
        )
    user.is_active = payload.is_active
    if payload.is_active:
        # Re-enabling an account also lifts any lockout left over from failed
        # login attempts, otherwise the user stays locked out after recovery.
        user.failed_login_attempts = 0
        user.locked_until = None
    db.commit()
    db.refresh(user)
    return user
