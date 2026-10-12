import base64
import json
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def list_audit_page(db: Session, limit: int, cursor: str | None) -> dict:
    statement = select(AuditLog).order_by(
        AuditLog.recorded_at.desc(), AuditLog.id.desc()
    )
    if cursor:
        try:
            values = json.loads(
                base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
            )
            if not isinstance(values, list) or len(values) != 2:
                raise ValueError
            if not all(isinstance(value, str) for value in values):
                raise ValueError
            timestamp, identifier = datetime.fromisoformat(values[0]), UUID(values[1])
            if timestamp.tzinfo is None:
                raise ValueError
        except (ValueError, TypeError, KeyError, base64.binascii.Error) as error:
            raise HTTPException(422, "Cursor nhật ký không hợp lệ.") from error
        statement = statement.where(
            tuple_(AuditLog.recorded_at, AuditLog.id) < tuple_(timestamp, identifier)
        )
    rows = list(db.scalars(statement.limit(limit + 1)))
    items = rows[:limit]
    next_cursor = None
    if len(rows) > limit:
        last = items[-1]
        next_cursor = (
            base64.urlsafe_b64encode(
                json.dumps([last.recorded_at.isoformat(), str(last.id)]).encode()
            )
            .decode()
            .rstrip("=")
        )
    return {"items": items, "next_cursor": next_cursor}
