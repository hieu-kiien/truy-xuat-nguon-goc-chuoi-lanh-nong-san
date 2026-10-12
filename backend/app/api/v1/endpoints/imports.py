from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.services.csv_import_service import (
    MAX_BYTES,
    eligible_import_organizations,
    import_csv,
)

router = APIRouter()


@router.get("/organizations")
@require_permission("products:write")
def import_organizations(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    if principal.role != "system_admin":
        raise HTTPException(403, "Chỉ quản trị hệ thống được nhập CSV.")
    return eligible_import_organizations(db)


@router.post("/{kind}", status_code=201)
@require_permission("products:write")
async def upload_csv(
    kind: Literal["products", "farms"],
    request: Request,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, int]:
    if principal.role != "system_admin":
        raise HTTPException(403, "Chỉ quản trị hệ thống được nhập CSV.")
    if request.headers.get("content-type", "").split(";", 1)[0].strip() != "text/csv":
        raise HTTPException(415, "Gửi tệp CSV với Content-Type text/csv.")
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > MAX_BYTES:
            raise HTTPException(413, "Tệp CSV vượt giới hạn 1 MiB.")
        data.extend(chunk)
    created = await run_in_threadpool(import_csv, db, principal, bytes(data), kind)
    return {"created": created}
