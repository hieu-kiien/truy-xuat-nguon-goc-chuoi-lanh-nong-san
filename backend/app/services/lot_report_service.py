"""Xuất hồ sơ truy xuất của một lô ra PDF kèm kết quả kiểm toàn vẹn (N3-72).

Hồ sơ gồm thông tin lô, kết quả đối chiếu chuỗi SHA-256 tại thời điểm xuất và
toàn bộ sự kiện mà người dùng được phép xem. Việc kiểm tra chỉ đọc, không ghi
thêm bản ghi `integrity_checks` để endpoint tải tệp không tạo tác dụng phụ.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.core.tenancy import get_tenant_record
from app.models.farm import Farm
from app.models.identity import Organization
from app.models.lot import Lot
from app.services import event_service

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT_NAME = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"
VIETNAM_TIMEZONE = timezone(timedelta(hours=7))

EVENT_TYPE_LABELS: dict[str, str] = {
    "harvest_recorded": "Thu hoạch",
    "lot_split": "Tách lô",
    "lot_moved": "Di chuyển nội bộ",
    "lot_consumed": "Tiêu thụ",
    "lot_merged": "Gộp lô",
    "lot_derived": "Tạo lô từ lô nguồn",
    "handover_pending": "Đề nghị bàn giao",
    "handover_accepted": "Xác nhận nhận lô",
    "handover_rejected": "Từ chối nhận lô",
    "cold_storage": "Bảo quản kho lạnh",
    "cold_chain_violation": "Cảnh báo chuỗi lạnh",
    "shipment_loaded": "Xếp lên chuyến vận chuyển",
    "shipment_unloaded": "Dỡ khỏi chuyến vận chuyển",
    "recall_opened": "Mở thu hồi",
    "recall_confirmed": "Xác nhận thu hồi",
    "recall_completed": "Hoàn tất thu hồi",
}

LOT_STATUS_LABELS: dict[str, str] = {
    "active": "Đang lưu hành",
    "pending_handover": "Chờ bàn giao",
    "closed": "Đã đóng",
    "consumed": "Đã tiêu thụ",
}

ISSUE_LABELS: dict[str, str] = {
    "missing_event": "Thiếu sự kiện trong chuỗi",
    "content_hash_mismatch": "Nội dung sự kiện không khớp mã băm",
    "previous_hash_mismatch": "Liên kết đến sự kiện trước không khớp",
    "downstream_unverified": "Không thể xác minh các sự kiện tiếp theo",
}


def _register_fonts() -> None:
    """Nạp font Unicode (có đủ dấu tiếng Việt) một lần cho toàn tiến trình."""
    registered = set(pdfmetrics.getRegisteredFontNames())
    if FONT_NAME not in registered:
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_DIR / "DejaVuSans.ttf")))
    if FONT_BOLD not in registered:
        pdfmetrics.registerFont(
            TTFont(FONT_BOLD, str(FONT_DIR / "DejaVuSans-Bold.ttf"))
        )
    # Map thẻ <b> trong Paragraph sang font đậm Unicode; nếu không đăng ký family,
    # ReportLab quay về Helvetica-Bold và làm mất dấu tiếng Việt.
    pdfmetrics.registerFontFamily(
        FONT_NAME,
        normal=FONT_NAME,
        bold=FONT_BOLD,
        italic=FONT_NAME,
        boldItalic=FONT_BOLD,
    )


def report_file_name(lot_code: str) -> str:
    """Tên tệp tải về, chỉ giữ ký tự an toàn cho header Content-Disposition."""
    safe_code = re.sub(r"[^A-Za-z0-9_-]+", "-", lot_code).strip("-_")
    return f"ho-so-truy-xuat-{safe_code or 'lo'}.pdf"


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(VIETNAM_TIMEZONE).strftime("%d/%m/%Y %H:%M")


def _format_date(value) -> str:
    return value.strftime("%d/%m/%Y") if value else "—"


def _short_json(payload: dict[str, Any], limit: int = 320) -> str:
    if not payload:
        return "—"
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if len(text) > limit:
        return f"{text[:limit]}…"
    return text


def _safe(value: Any) -> str:
    """Escape a value before it is placed inside ReportLab markup.

    ReportLab parses a paragraph as mini XML, so a lot name or an event note
    that contains & or < would otherwise break the whole export.
    """
    return escape(str(value))


def _hash_lines(value: str, width: int = 32) -> str:
    """Chia mã băm dài thành dòng ngắn để không tràn lề khi in."""
    return "<br/>".join(
        _safe(value[index : index + width]) for index in range(0, len(value), width)
    )


def build_lot_trace_report(db: Session, principal: Principal, lot_id: UUID) -> dict:
    """Tập hợp dữ liệu hồ sơ; người dùng chỉ thấy sự kiện họ được phép xem."""
    lot = get_tenant_record(db, Lot, lot_id, principal)
    canonical_events = event_service.list_events_for_lot(db, principal, lot_id)
    integrity = event_service.verify_event_chain(canonical_events)
    visible_events = event_service.readable_events(db, principal, canonical_events)

    farm = db.get(Farm, lot.farm_id) if lot.farm_id else None
    owner = db.get(Organization, lot.organization_id)
    generated_at = datetime.now(UTC)
    code = lot.lot_code or str(lot.id)[:8]

    events = []
    first_invalid = integrity["first_invalid_sequence"]
    for event in visible_events:
        if first_invalid is not None and event.sequence_number >= first_invalid:
            status = (
                "invalid" if event.sequence_number == first_invalid else "unverified"
            )
        else:
            status = "valid"
        events.append(
            {
                "sequence_number": event.sequence_number,
                "recorded_at": event.recorded_at,
                "event_type": event.event_type,
                "event_label": EVENT_TYPE_LABELS.get(
                    event.event_type, event.event_type
                ),
                "organization_name": event.organization_name,
                "payload": event.payload,
                "payload_redacted": event.payload_redacted,
                "event_hash": event.event_hash,
                "status": status,
            }
        )

    return {
        "generated_at": generated_at,
        "lot": {
            "id": str(lot.id),
            "code": code,
            "name": lot.name,
            "product_name": lot.product.name if lot.product else None,
            "product_unit": lot.product.unit if lot.product else None,
            "harvested_on": lot.harvested_on,
            "quantity": lot.quantity,
            "remaining_quantity": lot.remaining_quantity,
            "status": lot.status,
            "status_label": LOT_STATUS_LABELS.get(lot.status, lot.status),
            "holder_name": lot.current_holder_organization_name,
            "owner_name": owner.name if owner else None,
            "location_name": lot.current_location.name
            if lot.current_location
            else None,
            "location_address": (
                lot.current_location.address if lot.current_location else None
            ),
            "farm_name": farm.name if farm else None,
            "farm_area_ha": farm.area_ha if farm else None,
        },
        "integrity": integrity,
        "events": events,
        "last_event_hash": (
            canonical_events[-1].event_hash if canonical_events else None
        ),
        "total_events": len(canonical_events),
    }


def _styles() -> dict[str, ParagraphStyle]:
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            fontName=FONT_BOLD,
            fontSize=17,
            leading=21,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#14532d"),
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            fontName=FONT_NAME,
            fontSize=10.5,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#334155"),
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "SectionHeading",
            fontName=FONT_BOLD,
            fontSize=11.5,
            leading=15,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=10,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName=FONT_NAME,
            fontSize=9,
            leading=12,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#1e293b"),
        ),
        "small": ParagraphStyle(
            "Small",
            fontName=FONT_NAME,
            fontSize=7.6,
            leading=9.6,
            textColor=colors.HexColor("#1e293b"),
            splitLongWords=1,
        ),
        "small_bold": ParagraphStyle(
            "SmallBold",
            fontName=FONT_BOLD,
            fontSize=7.8,
            leading=9.8,
            textColor=colors.HexColor("#0f172a"),
        ),
        "note": ParagraphStyle(
            "Note",
            fontName=FONT_NAME,
            fontSize=7.8,
            leading=10.5,
            textColor=colors.HexColor("#475569"),
        ),
    }


def _facts_table(lot: dict, styles: dict[str, ParagraphStyle]) -> Table:
    unit = lot.get("product_unit") or ""
    quantity = lot.get("quantity")
    remaining = lot.get("remaining_quantity")
    rows = [
        ("Mã lô", lot["code"]),
        ("Tên lô", lot["name"]),
        ("Sản phẩm", lot.get("product_name") or "—"),
        ("Ngày thu hoạch", _format_date(lot.get("harvested_on"))),
        ("Khối lượng ban đầu", f"{quantity} {unit}".strip() if quantity else "—"),
        (
            "Khối lượng còn lại",
            f"{remaining} {unit}".strip() if remaining is not None else "—",
        ),
        ("Trạng thái", lot.get("status_label") or "—"),
        ("Đơn vị đang giữ", lot.get("holder_name") or "—"),
        ("Đơn vị sở hữu lô", lot.get("owner_name") or "—"),
        ("Vùng trồng", lot.get("farm_name") or "—"),
        (
            "Địa điểm hiện tại",
            " · ".join(
                part
                for part in (lot.get("location_name"), lot.get("location_address"))
                if part
            )
            or "—",
        ),
        ("Mã lô (UUID)", lot["id"]),
    ]
    body = [
        [
            Paragraph(f"<b>{label}</b>", styles["small"]),
            Paragraph(_safe(value), styles["small"]),
        ]
        for label, value in rows
    ]
    table = Table(body, colWidths=[42 * mm, 132 * mm])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _integrity_block(
    integrity: dict, generated_at: datetime, styles: dict[str, ParagraphStyle]
) -> list:
    valid = bool(integrity["valid"])
    heading = "Chuỗi sự kiện hợp lệ" if valid else "Phát hiện sai lệch chuỗi sự kiện"
    detail = (
        f"Đã kiểm tra {integrity['checked_events']} sự kiện. "
        "Toàn bộ liên kết băm khớp với dữ liệu đã ghi."
        if valid
        else (
            f"Đã kiểm tra {integrity['checked_events']} sự kiện. "
            f"Sai lệch đầu tiên tại sự kiện {integrity['first_invalid_sequence']}."
        )
    )
    issue_rows = [
        [
            Paragraph(f"Sự kiện {issue.sequence_number}", styles["small"]),
            Paragraph(_safe(ISSUE_LABELS.get(issue.kind, issue.kind)), styles["small"]),
        ]
        for issue in integrity["issues"]
    ]
    content = [
        Paragraph(
            heading,
            ParagraphStyle(
                "IntegrityHeading",
                fontName=FONT_BOLD,
                fontSize=11,
                leading=14,
                textColor=colors.HexColor("#166534" if valid else "#991b1b"),
                alignment=TA_LEFT,
            ),
        ),
        Spacer(1, 3),
        Paragraph(_safe(detail), styles["small"]),
        Spacer(1, 3),
        Paragraph(
            f"Thời điểm kiểm tra: {_format_datetime(generated_at)} (GMT+7)",
            styles["note"],
        ),
    ]
    if issue_rows:
        issue_table = Table(
            [
                [
                    Paragraph("<b>Sự kiện</b>", styles["small_bold"]),
                    Paragraph("<b>Loại sai lệch</b>", styles["small_bold"]),
                ]
            ]
            + issue_rows,
            colWidths=[28 * mm, 120 * mm],
        )
        issue_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#f3c4c4")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fde8e8")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        content.extend([Spacer(1, 4), issue_table])
    box = Table([[content]], colWidths=[174 * mm])
    box.setStyle(
        TableStyle(
            [
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.9,
                    colors.HexColor("#16a34a" if valid else "#dc2626"),
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#f0fdf4" if valid else "#fef2f2"),
                ),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return [box]


def _events_table(
    events: list[dict], styles: dict[str, ParagraphStyle]
) -> Table | Paragraph:
    if not events:
        return Paragraph("Lô chưa có sự kiện nào được ghi nhận.", styles["body"])
    status_labels = {
        "valid": "Hợp lệ",
        "invalid": "Sai lệch",
        "unverified": "Chưa xác minh",
    }
    header = [
        "#",
        "Thời điểm (GMT+7)",
        "Loại sự kiện",
        "Đơn vị ghi nhận",
        "Nội dung",
        "Mã băm",
        "Trạng thái",
    ]
    rows = [[Paragraph(f"<b>{item}</b>", styles["small_bold"]) for item in header]]
    for event in events:
        payload = (
            "(nội dung bị ẩn do ngoài phạm vi được xem)"
            if event["payload_redacted"]
            else _short_json(event["payload"])
        )
        rows.append(
            [
                Paragraph(str(event["sequence_number"]), styles["small"]),
                Paragraph(_format_datetime(event["recorded_at"]), styles["small"]),
                Paragraph(_safe(event["event_label"]), styles["small"]),
                Paragraph(_safe(event["organization_name"] or "—"), styles["small"]),
                Paragraph(_safe(payload), styles["small"]),
                Paragraph(f"{event['event_hash'][:12]}…", styles["small"]),
                Paragraph(status_labels[event["status"]], styles["small"]),
            ]
        )
    table = Table(
        rows,
        colWidths=[7 * mm, 22 * mm, 30 * mm, 28 * mm, 52 * mm, 18 * mm, 17 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]
        )
    )
    return table


def render_lot_trace_pdf(report: dict) -> bytes:
    """Kết xuất hồ sơ đã chuẩn bị thành tệp PDF A4."""
    _register_fonts()
    styles = _styles()
    buffer = BytesIO()
    lot = report["lot"]
    title_code = lot["code"]

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=f"Hồ sơ truy xuất lô {title_code}",
        author="AgroChain",
        subject="Hồ sơ truy xuất nguồn gốc và kết quả kiểm toàn vẹn",
    )

    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont(FONT_NAME, 7.5)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(
            18 * mm,
            10 * mm,
            f"AgroChain · Hồ sơ truy xuất lô {title_code} · Xuất lúc "
            f"{_format_datetime(report['generated_at'])} (GMT+7)",
        )
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Trang {doc.page}")
        canvas.restoreState()

    story: list = [
        Paragraph("HỒ SƠ TRUY XUẤT NGUỒN GỐC", styles["title"]),
        Paragraph(
            f"Lô <b>{_safe(title_code)}</b>"
            + (f" · {_safe(lot['product_name'])}" if lot.get("product_name") else ""),
            styles["subtitle"],
        ),
        Paragraph("1. Thông tin lô hàng", styles["h2"]),
        _facts_table(lot, styles),
        Paragraph("2. Kết quả kiểm tra toàn vẹn", styles["h2"]),
        *_integrity_block(report["integrity"], report["generated_at"], styles),
        Spacer(1, 4),
        Paragraph(
            "Kết quả kiểm tra được tính lại từ chuỗi sự kiện tại thời điểm xuất hồ sơ. "
            "Cơ chế đối chiếu SHA-256 giúp phát hiện dữ liệu bị sửa hoặc thiếu so với "
            "chuỗi đã ghi; tài liệu này không phải chữ ký số và không thay thế kết luận "
            "pháp lý hay giám định độc lập.",
            styles["note"],
        ),
        PageBreak(),
        Paragraph(
            f"3. Lịch sử sự kiện đầy đủ ({report['total_events']} sự kiện)",
            styles["h2"],
        ),
        Paragraph(
            "Thứ tự theo số thứ tự trong chuỗi băm. Trạng thái Hợp lệ nghĩa là sự kiện "
            "và liên kết băm của nó khớp dữ liệu đã ghi.",
            styles["note"],
        ),
        Spacer(1, 5),
        _events_table(report["events"], styles),
        Spacer(1, 8),
        KeepTogether(
            [
                Paragraph("4. Thông tin đối chiếu", styles["h2"]),
                Paragraph(
                    "Mã băm sự kiện cuối cùng:"
                    f"<br/><font face='Courier' size='7'>"
                    f"{_hash_lines(report['last_event_hash'] or '—')}</font>",
                    styles["small"],
                ),
                Spacer(1, 3),
                Paragraph(
                    f"Hồ sơ được tạo tự động bởi hệ thống AgroChain cho lô {_safe(title_code)}. "
                    "Người xem có thể đối chiếu mã băm cuối cùng với API kiểm tra toàn vẹn "
                    "của lô để xác nhận tài liệu chưa bị thay đổi.",
                    styles["note"],
                ),
            ]
        ),
    ]
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
