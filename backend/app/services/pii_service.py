"""Erase identifying data without breaking the event hash chain (N3-75).

Two rules make this safe:

1. The hash of an event covers only the event columns, never a live join to a
   user, an organization or a farm. So erasing identity data outside the
   ``events`` table leaves every existing ``event_hash`` untouched and
   ``verify_event_chain`` keeps returning valid.
2. New events must not carry identity data into the hashed content. The
   writers now reference entities by id only, and
   :func:`app.services.event_service.assert_payload_has_no_identity` rejects a
   payload that would put a name, an email, a phone number or an address into
   the chain.

What the erase touches: the name, the email and the coordinates of the
growing organization, its farm and its accounts. What it cannot touch: the
events written before this change, and the free-text notes a user typed. Those
are accepted residual risks, recorded in the risk register (R-06).
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.core.tenancy import get_tenant_record, tenant_select
from app.models.farm import Farm
from app.models.identity import Organization
from app.models.pii_request import PiiAnonymizationRequest
from app.services import public_trace_cache

logger = logging.getLogger(__name__)

STATUS_REQUESTED = "requested"
STATUS_COMPLETED = "completed"


def request_anonymization(
    db: Session,
    principal: Principal,
    farm_id: UUID,
    reason: str | None,
) -> PiiAnonymizationRequest:
    """Record a request to erase the identifying data of a growing organization."""
    farm = get_tenant_record(db, Farm, farm_id, principal)
    if farm.latitude is None and farm.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vùng trồng này đã được ẩn danh trước đó.",
        )
    existing_open = db.scalar(
        select(PiiAnonymizationRequest.id).where(
            PiiAnonymizationRequest.farm_id == farm.id,
            PiiAnonymizationRequest.status == STATUS_REQUESTED,
        )
    )
    if existing_open is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Đã có yêu cầu ẩn danh đang chờ xử lý cho vùng trồng này.",
        )
    request = PiiAnonymizationRequest(
        organization_id=principal.organization_id,
        farm_id=farm.id,
        requested_by_user_id=principal.user_id,
        requested_at=datetime.now(UTC),
        reason=reason,
        status=STATUS_REQUESTED,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def list_anonymization_requests(
    db: Session, principal: Principal, *, limit: int = 50
) -> list[PiiAnonymizationRequest]:
    """List the requests the caller may see, newest first."""
    statement = tenant_select(PiiAnonymizationRequest, principal)
    return list(
        db.scalars(
            statement.order_by(PiiAnonymizationRequest.requested_at.desc()).limit(limit)
        ).all()
    )


def execute_anonymization(
    db: Session, principal: Principal, request_id: UUID
) -> PiiAnonymizationRequest:
    """Erase the identifying data of the organization that asked for it.

    The event log is never touched, so the hash chain of every related lot
    stays valid.
    """
    request = db.scalar(
        select(PiiAnonymizationRequest).where(PiiAnonymizationRequest.id == request_id)
    )
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy yêu cầu ẩn danh.",
        )
    if request.status == STATUS_COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Yêu cầu này đã được thực hiện.",
        )

    farm = db.get(Farm, request.farm_id)
    organization = db.get(Organization, request.organization_id)
    if farm is None or organization is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tổ chức hoặc vùng trồng không còn tồn tại.",
        )

    # The erase reaches rows of another organization, so it runs as one
    # bounded privileged function. The event log is never touched, so every
    # hash of every related lot stays valid.
    db.execute(
        text("SELECT public.app_anonymize_organization(:organization, :farm)"),
        {"organization": request.organization_id, "farm": request.farm_id},
    )

    now = datetime.now(UTC)
    request.status = STATUS_COMPLETED
    request.decided_by_user_id = principal.user_id
    request.executed_at = now
    db.commit()
    db.refresh(request)
    # The public trace of every lot of this farm changed, so the cached
    # projection must not keep the old name.
    public_trace_cache.invalidate_all()
    logger.info(
        "Anonymized organization_id=%s farm_id=%s by user_id=%s",
        request.organization_id,
        request.farm_id,
        principal.user_id,
    )
    return request
