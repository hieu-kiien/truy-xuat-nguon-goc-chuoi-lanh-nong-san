import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, false, func, select
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.core.authorization import has_permission

logger = logging.getLogger(__name__)
SHARED_TABLE_NAMES = frozenset({"products", "product_cold_chain_configs"})


def lot_is_historical(model: Any, principal: Principal):
    """Former custodians may read history but never current logistics fields."""
    if principal.role in {"inspector", "system_admin"}:
        return false()
    return and_(
        model.current_holder_organization_id != principal.organization_id,
        func.app_event_cutoff(model.id).is_not(None),
    )


def _require_tenant_column(model: Any) -> None:
    if "organization_id" not in model.__table__.c:
        raise TypeError(f"{model.__name__} must have an organization_id column")


def tenant_select(model: Any, principal: Principal | None = None):
    """Build a database-filtered query for an organization-owned model."""
    if principal is None:
        raise ValueError("Tenant context is required for organization-owned queries")

    _require_tenant_column(model)

    if principal.role == "system_admin":
        return select(model)

    if model.__tablename__ in ("farms", "lots", "events") and has_permission(
        principal.role, f"{model.__tablename__}:read_all"
    ):
        return select(model)

    if model.__tablename__ == "lots":
        return select(model).where(
            model.current_holder_organization_id == principal.organization_id
        )

    return select(model).where(model.organization_id == principal.organization_id)


def shared_select(model: Any):
    """Build an unscoped query for an explicitly registered global table."""
    table_name = model.__tablename__
    if table_name not in SHARED_TABLE_NAMES:
        raise TypeError(f"{table_name} is not registered as a shared table")
    if "organization_id" in model.__table__.c:
        raise TypeError(f"Shared table {table_name} must not have organization_id")
    return select(model)


def get_tenant_record(
    db: Session,
    model: Any,
    record_id: UUID,
    principal: Principal,
    *,
    allow_historical: bool = False,
) -> Any:
    """Fetch one visible row; never query around RLS to detect foreign rows."""
    statement = tenant_select(model, principal).where(model.id == record_id)
    if model.__tablename__ in {"lots", "events"}:
        # These reads include provenance and pre-transfer history. PostgreSQL's
        # policies define that scope; mutation services still require custody.
        statement = select(model).where(model.id == record_id)
        if model.__tablename__ == "lots" and not allow_historical:
            statement = statement.where(~lot_is_historical(model, principal))
    record = db.scalar(statement)
    if record is not None:
        return record

    logger.warning(
        "Denied access to a record not visible to the caller "
        "user_id=%s organization_id=%s resource_type=%s resource_id=%s",
        principal.user_id,
        principal.organization_id,
        model.__tablename__,
        record_id,
        extra={
            "event": "authorization.record_not_visible",
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
