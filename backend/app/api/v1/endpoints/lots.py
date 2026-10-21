from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.auth import Principal, extract_session_token, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.core.security import hash_session_token
from app.models.lot import Lot
from app.schemas.lineage import (
    LineageRead,
    LotDetailRead,
    LotMerge,
    LotSplit,
    SplitRead,
)
from app.schemas.location import LotConsume, LotMove
from app.schemas.lot import (
    InputLotCreate,
    InputLotRead,
    LotCreate,
    LotListRead,
    LotRead,
)
from app.schemas.processing import (
    ProcessingStepRecordCreate,
    ProcessingStepRecordRead,
)
from app.schemas.recall import RecallReport
from app.services import (
    input_lot_service,
    lineage_service,
    lot_lifecycle_service,
    lot_report_service,
    lot_service,
    processing_step_service,
    recall_service,
    traversal_service,
)

router = APIRouter()


@router.post("/{lot_id}/move", response_model=LotRead)
@require_permission("locations:manage")
def move_lot(
    lot_id: UUID,
    payload: LotMove,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    return lot_lifecycle_service.move_lot(db, principal, lot_id, payload)


@router.post("/{lot_id}/consume", response_model=LotRead)
@require_permission("lots:consume")
def consume_lot(
    lot_id: UUID,
    payload: LotConsume,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    return lot_lifecycle_service.consume_lot(db, principal, lot_id, payload)


@router.post("/", response_model=LotRead, status_code=status.HTTP_201_CREATED)
@require_permission("lots:create")
def create_lot(
    payload: LotCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Lot:
    return lot_service.create_harvest_lot(db, principal, payload)


@router.get("/", response_model=LotListRead)
@require_permission("lots:read")
def list_lots(
    request: Request,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[
        str | None,
        Query(
            max_length=100, description="Tìm theo mã lô (không phân biệt hoa thường)"
        ),
    ] = None,
    product_id: Annotated[UUID | None, Query(description="Lọc theo sản phẩm")] = None,
    farm_id: Annotated[
        UUID | None, Query(description="Lọc theo vùng trồng (mã trang trại)")
    ] = None,
    harvested_from: Annotated[
        date | None, Query(description="Ngày thu hoạch bắt đầu (YYYY-MM-DD)")
    ] = None,
    harvested_to: Annotated[
        date | None, Query(description="Ngày thu hoạch kết thúc (YYYY-MM-DD)")
    ] = None,
    cursor: Annotated[str | None, Query(max_length=256)] = None,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    token = extract_session_token(request)
    session_token_hash = hash_session_token(token) if token else ""
    return lot_service.list_lots(
        db,
        principal,
        query=q,
        product_id=product_id,
        farm_id=farm_id,
        harvested_from=harvested_from,
        harvested_to=harvested_to,
        cursor=cursor,
        page_size=page_size,
        client_ip=request.client.host if request.client else None,
        session_token_hash=session_token_hash,
    )


@router.post("/merge", response_model=LotRead, status_code=status.HTTP_201_CREATED)
@require_permission("lots:transform")
def merge_lots(
    payload: LotMerge,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Lot:
    return lineage_service.merge_lots(db, principal, payload)


@router.post(
    "/{lot_id}/split", response_model=SplitRead, status_code=status.HTTP_201_CREATED
)
@require_permission("lots:transform")
def split_lot(
    lot_id: UUID,
    payload: LotSplit,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    return lineage_service.split_lot(db, principal, lot_id, payload)


@router.get("/{lot_id}/lineage", response_model=LineageRead)
@require_permission("lots:read")
def get_lineage(
    lot_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    direction: Literal["ancestors", "descendants"] = "ancestors",
) -> dict:
    return traversal_service.get_lineage(db, principal, lot_id, direction)


@router.get("/{lot_id}/input-lots", response_model=list[InputLotRead])
@require_permission("input_lots:read")
def list_input_lots(
    lot_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> list[InputLotRead]:
    """List the input materials recorded for a lot (N3-38)."""
    return input_lot_service.list_input_lots(db, principal, lot_id)


@router.post(
    "/{lot_id}/input-lots",
    response_model=list[InputLotRead],
    status_code=status.HTTP_201_CREATED,
)
@require_permission("input_lots:create")
def create_input_lots(
    lot_id: UUID,
    payload: InputLotCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> list[InputLotRead]:
    """Record the input materials used for a lot (N3-38)."""
    return input_lot_service.declare_input_lots(db, principal, lot_id, payload)


@router.get("/{lot_id}/processing-steps", response_model=list[ProcessingStepRecordRead])
@require_permission("processing_steps:read")
def list_processing_steps(
    lot_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ProcessingStepRecordRead]:
    """List the processing steps recorded for a lot (N3-27)."""
    return processing_step_service.list_processing_steps(db, principal, lot_id)


@router.post(
    "/{lot_id}/processing-steps",
    response_model=ProcessingStepRecordRead,
    status_code=status.HTTP_201_CREATED,
)
@require_permission("processing_steps:create")
def record_processing_step(
    lot_id: UUID,
    payload: ProcessingStepRecordCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> ProcessingStepRecordRead:
    """Record a processing step; it becomes one event on the lot chain (N3-27)."""
    return processing_step_service.record_processing_step(
        db, principal, lot_id, payload
    )


@router.get("/{lot_id}", response_model=LotDetailRead)
@require_permission("lots:read")
def get_lot(
    lot_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    return traversal_service.get_detail(db, principal, lot_id)


@router.get(
    "/{lot_id}/report.pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
@require_permission("lots:read")
def export_lot_report(
    lot_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Tải hồ sơ truy xuất đầy đủ của lô dưới dạng PDF (N3-72).

    Hồ sơ gồm thông tin lô, kết quả kiểm tra toàn vẹn chuỗi băm tại thời điểm
    xuất và toàn bộ sự kiện người gọi được phép xem. Endpoint chỉ đọc.
    """
    report = lot_report_service.build_lot_trace_report(db, principal, lot_id)
    pdf = lot_report_service.render_lot_trace_pdf(report)
    filename = lot_report_service.report_file_name(report["lot"]["code"])
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/{lot_id}/recall", response_model=RecallReport)
@require_permission("lots:read")
def get_lot_recall(
    lot_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    return recall_service.get_recall_report(db, principal, lot_id)
