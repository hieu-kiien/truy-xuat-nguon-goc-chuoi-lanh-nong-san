import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import Principal

logger = logging.getLogger(__name__)


def tenant_select(model: Any, principal: Principal, *, allow_inspector_all_lots: bool = False):
    """Build a DB-level organization filter for a tenant-owned model.

    Only lot-list callers should enable the inspector exception. Farm and other
    organization-owned records always remain scoped to the caller's organization.
    """
    if "organization_id" not in model.__table__.c:
        raise TypeError(f"{model.__name__} must have an organization_id column")

    if allow_inspector_all_lots and principal.role == "inspector":
        return select(model)

    return select(model).where(model.organization_id == principal.organization_id)


def get_tenant_record(
    db: Session, model: Any, record_id: UUID, principal: Principal
) -> Any:
    """Fetch a tenant record in SQL and log cross-organization IDOR attempts."""
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

    exists = db.scalar(select(model.id).where(model.id == record_id))
    if exists is not None:
        logger.warning(
            "Denied cross-organization record access",
            extra={
                "event": "authorization.cross_organization_access",
                "user_id": str(principal.user_id),
                "organization_id": str(principal.organization_id),
                "resource_type": model.__tablename__,
                "resource_id": str(record_id),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập dữ liệu của tổ chức khác.",
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy dữ liệu."
    )
