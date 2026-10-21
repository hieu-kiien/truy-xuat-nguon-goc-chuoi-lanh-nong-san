"""Danh sách trường công khai cho trang truy xuất công khai (S-48).

Nguyên tắc: mặc định MỌI trường dữ liệu lô là nội bộ. Chỉ những trường nằm
trong PUBLIC_TRACE_FIELDS mới được trả về cho khách chưa đăng nhập. Thêm bớt
trường công khai phải sửa danh sách này và chạy test_public_trace.
"""

from typing import Any

PUBLIC_TRACE_FIELDS = frozenset(
    {
        "lot_code",
        "product_name",
        "product_unit",
        "harvested_on",
        "farm_name",
        "origin_organization_type",
        "status",
        "recall_active",
        "cold_chain_violation",
        "processing_summary",
    }
)

# Tên tổ chức trung gian KHÔNG được lộ; chỉ hiện theo loại (NFR của S-48).
# Riêng vùng trồng hiện tên để người tiêu dùng truy xuất được nông hộ.
ORGANIZATION_TYPE_LABELS = {
    "farm": "Vùng trồng",
    "cooperative": "Hợp tác xã",
    "transport": "Đơn vị vận chuyển",
    "distribution": "Đơn vị phân phối",
    "inspection": "Cơ quan kiểm tra",
    "administration": "Quản trị hệ thống",
}

LOT_STATUS_LABELS = {
    "active": "Đang lưu thông",
    "pending_handover": "Chờ bàn giao",
    "closed": "Đã đóng lô",
    "consumed": "Đã tiêu thụ",
}


def build_public_trace(row: dict[str, Any]) -> dict[str, Any]:
    """Dựng phản hồi công khai bằng cách chọn đúng danh sách cho phép."""
    harvested_on = row.get("harvested_on")
    raw: dict[str, Any] = {
        "lot_code": row.get("lot_code"),
        "product_name": row.get("product_name"),
        "product_unit": row.get("product_unit"),
        "harvested_on": harvested_on.isoformat() if harvested_on else None,
        "farm_name": row.get("farm_name"),
        "origin_organization_type": ORGANIZATION_TYPE_LABELS.get(
            row.get("origin_organization_type"), "Đơn vị tham gia chuỗi"
        ),
        "status": LOT_STATUS_LABELS.get(row.get("status"), "Không xác định"),
        "recall_active": bool(row.get("recall_active")),
        "cold_chain_violation": bool(row.get("cold_chain_violation")),
        "processing_summary": row.get("processing_summary") or None,
    }
    return {field: raw[field] for field in PUBLIC_TRACE_FIELDS if field in raw}
