"""Business service for cold chain telemetry ingestion and violation inspection (N3-60, S-41)."""

import logging
from datetime import UTC
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.models.shipment import Shipment, ShipmentLot
from app.models.telemetry import TemperatureReading
from app.schemas.telemetry import (
    TelemetryIngestRequest,
    TelemetryIngestResponse,
    TelemetryViolationRead,
)
from app.services.cold_chain_detector import detect_temperature_violations

logger = logging.getLogger(__name__)


def _can_access_shipment(db: Session, principal: Principal, shipment: Shipment) -> bool:
    """Check if the caller's organization has legitimate visibility into the shipment."""
    if principal.role in {"system_admin", "inspector"}:
        return True
    if shipment.organization_id == principal.organization_id:
        return True

    # Or caller holds lots currently assigned to the shipment
    holds_lot = db.scalar(
        select(ShipmentLot.id)
        .join(ShipmentLot.lot)
        .where(
            ShipmentLot.shipment_id == shipment.id,
            ShipmentLot.lot.has(
                current_holder_organization_id=principal.organization_id
            ),
        )
    )
    return holds_lot is not None


def ingest_telemetry_readings(
    db: Session,
    principal: Principal,
    payload: TelemetryIngestRequest,
) -> TelemetryIngestResponse:
    """Ingest a batch of container temperature readings (S-41)."""
    # 1. Find active in_transit shipment for the container
    container_code = payload.container_code.strip()
    shipment = db.scalar(
        select(Shipment).where(
            Shipment.container_code == container_code,
            Shipment.status == "in_transit",
        )
    )
    if not shipment:
        logger.warning(
            "Telemetry ingest rejected: No in_transit shipment for container %s",
            container_code,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy chuyến xe đang vận chuyển (in_transit) gắn với thùng lạnh '{container_code}'.",
        )

    # 2. Authorization: carrier organization or system_admin
    if (
        principal.role != "system_admin"
        and shipment.organization_id != principal.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ đơn vị vận chuyển của chuyến xe mới được nạp dữ liệu cảm biến.",
        )

    # 3. Sort readings chronologically
    sorted_items = sorted(payload.readings, key=lambda r: r.recorded_at)

    # 4. Check existing timestamps to calculate ingested vs duplicate counts
    existing_timestamps = set(
        db.scalars(
            select(TemperatureReading.recorded_at).where(
                TemperatureReading.shipment_id == shipment.id
            )
        ).all()
    )

    values_to_insert = []
    duplicate_count = 0

    for item in sorted_items:
        rec_at = item.recorded_at
        if rec_at.tzinfo is None:
            rec_at = rec_at.replace(tzinfo=UTC)

        if rec_at in existing_timestamps:
            duplicate_count += 1
            continue

        values_to_insert.append(
            {
                "shipment_id": shipment.id,
                "container_code": container_code,
                "temperature_celsius": item.temperature_celsius,
                "recorded_at": rec_at,
            }
        )

    if values_to_insert:
        stmt = insert(TemperatureReading).values(values_to_insert)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["shipment_id", "recorded_at"]
        )
        db.execute(stmt)
        db.commit()

    # 5. Fetch all readings for shipment to evaluate sliding-window violations
    all_readings = list(
        db.scalars(
            select(TemperatureReading)
            .where(TemperatureReading.shipment_id == shipment.id)
            .order_by(TemperatureReading.recorded_at.asc())
        ).all()
    )

    raw_violations = detect_temperature_violations(all_readings)
    violations_summary = [
        TelemetryViolationRead(
            violation_type=v.violation_type,
            started_at=v.started_at,
            ended_at=v.ended_at,
            duration_minutes=v.duration_minutes,
            peak_temperature_celsius=v.peak_temperature_celsius,
        )
        for v in raw_violations
    ]

    return TelemetryIngestResponse(
        container_code=container_code,
        shipment_id=shipment.id,
        shipment_code=shipment.shipment_code,
        ingested_count=len(values_to_insert),
        duplicate_count=duplicate_count,
        total_readings=len(all_readings),
        violations_detected=len(violations_summary),
        violations=violations_summary,
    )


def list_shipment_readings(
    db: Session,
    principal: Principal,
    shipment_id: UUID,
) -> list[TemperatureReading]:
    """Retrieve all temperature readings for a given shipment."""
    shipment = db.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy chuyến vận chuyển.",
        )

    if not _can_access_shipment(db, principal, shipment):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xem dữ liệu đo của chuyến xe này.",
        )

    return list(
        db.scalars(
            select(TemperatureReading)
            .where(TemperatureReading.shipment_id == shipment_id)
            .order_by(TemperatureReading.recorded_at.asc())
        ).all()
    )


def get_shipment_violations(
    db: Session,
    principal: Principal,
    shipment_id: UUID,
) -> list[TelemetryViolationRead]:
    """Detect and return confirmed temperature violations for a given shipment."""
    readings = list_shipment_readings(db, principal, shipment_id)
    raw = detect_temperature_violations(readings)
    return [
        TelemetryViolationRead(
            violation_type=v.violation_type,
            started_at=v.started_at,
            ended_at=v.ended_at,
            duration_minutes=v.duration_minutes,
            peak_temperature_celsius=v.peak_temperature_celsius,
        )
        for v in raw
    ]
