from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.core.authorization import can_read_across_organizations
from app.core.security_events import log_security_event


def tenant_select(
    model: Any,
    principal: Principal,
    *,
    allow_cross_tenant_read: bool = False,
):
    """Build a DB-level organization filter for a tenant-owned model.

    ``allow_cross_tenant_read`` is only meaningful for models that opt into
    cross-organization read access (currently lots). It is granted by the
    ``lots:read_all`` permission, not by a hard-coded role name, and it relaxes
    reads only: writes remain scoped to the caller's own organization.
    """
    if "organization_id" not in model.__table__.c:
        raise TypeError(f"{model.__name__} must have an organization_id column")

    if allow_cross_tenant_read and can_read_across_organizations(principal):
        return select(model)

    return select(model).where(model.organization_id == principal.organization_id)


def record_exists_outside_tenant(db: Session, model: Any, record_id: UUID) -> bool:
    """Whether a tenant-owned record exists at all, ignoring RLS visibility.

    Row-level security hides other tenants' rows, so an ordinary SELECT cannot
    tell "forbidden" from "does not exist". This delegates to the
    ``app_tenant_record_exists`` SECURITY DEFINER helper, which runs with
    ``row_security = off`` and returns only a boolean.
    """
    return bool(
        db.scalar(select(func.app_tenant_record_exists(model.__tablename__, record_id)))
    )


def get_tenant_record(
    db: Session, model: Any, record_id: UUID, principal: Principal
) -> Any:
    """Fetch a tenant record in SQL and log cross-organization IDOR attempts.

    A record that exists but belongs to another organization returns 403 and is
    logged as a security event; a record that does not exist returns 404.
    """
    if "organization_id" not in model.__table__.c:
        raise TypeError(f"{model.__name__} must have an organization_id column")

    record = db.scalar(
        select(model).where(
            model.id == record_id,
            model.organization_id == principal.organization_id,
        )
    )
    if record is not None:
        return record

    if record_exists_outside_tenant(db, model, record_id):
        log_security_event(
            "authorization.cross_organization_access",
            user_id=str(principal.user_id),
            organization_id=str(principal.organization_id),
            role=principal.role,
            resource_type=model.__tablename__,
            resource_id=str(record_id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập dữ liệu của tổ chức khác.",
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy dữ liệu."
    )
