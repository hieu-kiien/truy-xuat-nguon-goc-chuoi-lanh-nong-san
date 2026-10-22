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


def trace_lot_route(db: Session, lot_code: str) -> dict:
    """Trả về bản đồ hành trình công khai của một lô (N3-70).

    Toạ độ được làm tròn về cấp xã hoặc huyện, nên toạ độ chính xác của thửa
    không bao giờ ra ngoài hệ thống. Nếu vùng trồng đã được ẩn danh (không còn
    toạ độ), điểm đó không được phát ra bản đồ.
    """
    normalized = (lot_code or "").strip().upper()
    rows = (
        db.execute(
            text(
                "SELECT point_order, point_name, point_kind, "
                "point_latitude, point_longitude "
                "FROM public.app_public_lot_route(:lot_code)"
            ),
            {"lot_code": normalized},
        )
        .mappings()
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lô hàng với mã đã cung cấp.",
        )
    return {
        "points": [
            {
                "order": int(row["point_order"]),
                "name": row["point_name"] or "",
                "kind": row["point_kind"] or "stop",
                "latitude": float(row["point_latitude"]),
                "longitude": float(row["point_longitude"]),
            }
            for row in rows
            if row["point_latitude"] is not None and row["point_longitude"] is not None
        ]
    }


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
