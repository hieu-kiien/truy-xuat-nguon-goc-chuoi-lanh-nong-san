import base64
import json
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, set_db_context
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


def persist_audit_row(session_token_hash: str, row: AuditLog) -> None:
    """Ghi một bản ghi nhật ký tra cứu vào session riêng biệt.

    Dùng cho các thao tác chỉ đọc (ví dụ tra cứu lô) mà middleware nhật ký
    không ghi (chỉ ghi POST/PUT/PATCH/DELETE). Session riêng biệt tránh làm
    hết hạn (expire) các đối tượng ORM đang được dùng để serialize phản hồi
    của session nghiệp vụ chính.
    """
    with SessionLocal() as db:
        db.info["audit_fallback"] = True
        set_db_context(db, session_token_hash=session_token_hash)
        db.add(row)
        db.commit()
