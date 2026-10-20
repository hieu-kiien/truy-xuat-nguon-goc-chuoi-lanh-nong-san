"""Tra cứu công khai theo mã lô (S-48, S-49, S-50).

Phản hồi chỉ gồm các trường trong PUBLIC_TRACE_FIELDS; trạng thái thu hồi và
vi phạm chuỗi lạnh được diễn đạt thành cảnh báo cho người tiêu dùng, không lộ
số đo nhiệt độ hay thông tin đối tác.
"""

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.public_fields import build_public_trace
from app.services import public_trace_cache

RECALL_WARNING_MESSAGE = (
    "Lô hàng này đang nằm trong danh sách thu hồi. Không tiêu thụ sản phẩm có "
    "mã lô này; vui lòng liên hệ đơn vị bán hoặc cơ quan chức năng để được hướng dẫn."
)
COLD_CHAIN_NOTE_MESSAGE = (
    "Lô hàng này từng có cảnh báo trong quá trình bảo quản chuỗi lạnh."
)


def trace_lot_code(db: Session, lot_code: str) -> dict:
    """Trả về dữ liệu công khai của một lô theo mã lô."""
    normalized = (lot_code or "").strip().upper()

    cached = public_trace_cache.get(normalized)
    if cached is not None:
        return cached

    row = (
        db.execute(
            text("SELECT * FROM public.app_public_lot_trace(:lot_code)"),
            {"lot_code": normalized},
        )
        .mappings()
        .first()
    )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lô hàng với mã đã cung cấp.",
        )

    trace = build_public_trace(dict(row))

    warnings: list[dict] = []
    if trace["recall_active"]:
        warnings.append(
            {"code": "recall", "level": "danger", "message": RECALL_WARNING_MESSAGE}
        )
    if trace["cold_chain_violation"]:
        warnings.append(
            {"code": "cold_chain", "level": "note", "message": COLD_CHAIN_NOTE_MESSAGE}
        )

    payload = {"trace": trace, "warnings": warnings}
    public_trace_cache.put(normalized, payload)
    return payload
