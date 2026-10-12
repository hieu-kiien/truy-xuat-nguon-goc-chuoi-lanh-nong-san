from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.authorization import require_permission
from app.core.database import get_db
from app.services.audit_service import list_audit_page

router = APIRouter()


class AuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    recorded_at: datetime
    actor_user_id: UUID | None
    actor_name: str | None
    actor_authenticated: bool
    organization_id: UUID | None
    organization_name: str | None
    client_ip: str | None
    action: str
    object_type: str
    object_id: UUID | None
    outcome: str
    status_code: int
    reason: str | None


class AuditPage(BaseModel):
    items: list[AuditRead]
    next_cursor: str | None


@router.get("/", response_model=AuditPage)
@require_permission("security:read")
def list_audit(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> dict:
    return list_audit_page(db, limit, cursor)
