"""API endpoints for cold chain telemetry ingestion and violation inspection (N3-60, S-41)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.schemas.cold_chain_config import ShipmentColdChainLimitsRead
from app.schemas.cold_chain_stats import ColdChainViolationStatsRead
from app.schemas.telemetry import (
    TelemetryHourlyAggregateRead,
    TelemetryIngestRequest,
    TelemetryIngestResponse,
    TelemetryReadingRead,
    TelemetryViolationRead,
)
from app.services import (
    cold_chain_config_service,
    cold_chain_stats_service,
    telemetry_service,
)

router = APIRouter()


@router.post(
    "/readings",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a batch of cold chain container temperature readings (S-41)",
)
@require_permission("telemetry:ingest")
def ingest_readings(
    payload: TelemetryIngestRequest,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> TelemetryIngestResponse:
    return telemetry_service.ingest_telemetry_readings(db, principal, payload)


@router.get(
    "/shipments/{shipment_id}/readings",
    response_model=list[TelemetryReadingRead],
    summary="Get all temperature readings for a cold shipment",
)
@require_permission("telemetry:read")
def get_shipment_readings(
    shipment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
) -> list[TelemetryReadingRead]:
    """The readings of a shipment; the window narrows the moment recorded."""
    if from_time is not None and to_time is not None and from_time > to_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Khoang thoi gian phai bat dau truoc ket thuc.",
        )
    return telemetry_service.list_shipment_readings(
        db, principal, shipment_id, from_time=from_time, to_time=to_time
    )


@router.get(
    "/shipments/{shipment_id}/readings/hourly",
    response_model=list[TelemetryHourlyAggregateRead],
    summary="Chuoi nhiet do da tong hop theo gio cua chuyen van chuyen (N3-64)",
)
@require_permission("telemetry:read")
def get_shipment_hourly_aggregates(
    shipment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[TelemetryHourlyAggregateRead]:
    """The summarised hours of a shipment; empty hours stay visible as gaps."""
    return telemetry_service.list_hourly_aggregates(db, principal, shipment_id)


@router.get(
    "/shipments/{shipment_id}/cold-chain-limits",
    response_model=ShipmentColdChainLimitsRead,
    summary="Get the effective strictest cold chain limits of a cold shipment (N3-62)",
)
@require_permission("telemetry:read")
def get_shipment_cold_chain_limits(
    shipment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ShipmentColdChainLimitsRead:
    return cold_chain_config_service.read_shipment_limits(db, principal, shipment_id)


@router.get(
    "/shipments/{shipment_id}/violations",
    response_model=list[TelemetryViolationRead],
    summary="Get detected temperature violations for a cold shipment",
)
@require_permission("telemetry:read")
def get_shipment_violations(
    shipment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[TelemetryViolationRead]:
    return telemetry_service.get_shipment_violations(db, principal, shipment_id)


@router.get(
    "/violations/stats",
    response_model=ColdChainViolationStatsRead,
    summary="Thống kê vi phạm chuỗi lạnh theo đơn vị vận chuyển (N3-73)",
)
@require_permission("telemetry:read")
def get_cold_chain_violation_stats(
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    period_start: Annotated[
        datetime | None,
        Query(
            alias="from",
            description="Bắt đầu khoảng thời gian, theo thời điểm mở chuyến vận chuyển",
        ),
    ] = None,
    period_end: Annotated[
        datetime | None,
        Query(
            alias="to",
            description="Kết thúc khoảng thời gian, theo thời điểm mở chuyến vận chuyển",
        ),
    ] = None,
) -> ColdChainViolationStatsRead:
    """Aggregate cold chain violations per carrier organization.

    The window is applied to the moment a shipment was opened. Only violations
    that started inside the same window are attributed to those shipments.
    """
    return cold_chain_stats_service.summarize_violations_by_carrier(
        db,
        principal,
        period_start=period_start,
        period_end=period_end,
    )
