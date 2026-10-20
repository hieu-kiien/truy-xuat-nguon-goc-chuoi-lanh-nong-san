"""Business service for cold chain telemetry ingestion and violation inspection (N3-59, N3-60, N3-61, N3-62, N3-63)."""

import logging
from datetime import UTC
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.models.shipment import Shipment, ShipmentLot
from app.models.telemetry import ColdChainViolation, TemperatureReading
from app.schemas.telemetry import (
    TelemetryIngestRequest,
    TelemetryIngestResponse,
    TelemetryViolationRead,
)
from app.services import cold_chain_config_service, event_service
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


def sync_shipment_violations_and_events(
    db: Session,
    principal: Principal,
    shipment: Shipment,
    *,
    is_completing: bool = False,
) -> list[ColdChainViolation]:
    """Recompute sliding-window cold chain violations, persist records, settle closed excursions,

    and append immutable cold_chain_violation events to all active lots on the shipment (N3-61, N3-62, N3-63).
    """
    all_readings = list(
        db.scalars(
            select(TemperatureReading)
            .where(TemperatureReading.shipment_id == shipment.id)
            .order_by(TemperatureReading.recorded_at.asc())
        ).all()
    )

    limits, _from_snapshot = cold_chain_config_service.effective_shipment_limits(
        db, shipment
    )
    min_temp = float(
        shipment.cold_chain_min_temp_celsius
        if shipment.cold_chain_min_temp_celsius is not None
        else limits.min_temp_celsius
    )
    max_temp = float(
        shipment.cold_chain_max_temp_celsius
        if shipment.cold_chain_max_temp_celsius is not None
        else limits.max_temp_celsius
    )
    delay_min = int(
        shipment.cold_chain_delay_minutes
        if shipment.cold_chain_delay_minutes is not None
        else limits.delay_minutes
    )
    merge_gap = int(
        shipment.effective_merge_gap_minutes
        if shipment.effective_merge_gap_minutes is not None
        else 5
    )

    detected = detect_temperature_violations(
        all_readings,
        min_temp_celsius=min_temp,
        max_temp_celsius=max_temp,
        delay_minutes=delay_min,
        merge_gap_minutes=merge_gap,
    )

    last_reading_time = all_readings[-1].recorded_at if all_readings else None

    # Fetch existing violation records for this shipment
    existing_violations = {
        v.started_at: v
        for v in db.scalars(
            select(ColdChainViolation).where(
                ColdChainViolation.shipment_id == shipment.id
            )
        ).all()
    }

    persisted_records: list[ColdChainViolation] = []

    for v in detected:
        v_start = v.started_at
        if v_start.tzinfo is None:
            v_start = v_start.replace(tzinfo=UTC)
        v_end = v.ended_at
        if v_end.tzinfo is None:
            v_end = v_end.replace(tzinfo=UTC)

        rec = existing_violations.get(v_start)
        if rec is None:
            rec = ColdChainViolation(
                shipment_id=shipment.id,
                violation_type=v.violation_type,
                started_at=v_start,
                ended_at=v_end,
                duration_minutes=Decimal(str(v.duration_minutes)),
                peak_temperature_celsius=Decimal(str(v.peak_temperature_celsius)),
                is_settled=False,
            )
            db.add(rec)
            db.flush()
            existing_violations[v_start] = rec
        else:
            if not rec.is_settled:
                rec.ended_at = v_end
                rec.duration_minutes = Decimal(str(v.duration_minutes))
                rec.peak_temperature_celsius = Decimal(str(v.peak_temperature_celsius))
                db.flush()

        persisted_records.append(rec)

    # Determine which violations can be settled
    # A violation is eligible to settle when the excursion has permanently closed:
    # 1. The shipment is completing (is_completing=True or shipment.status == 'completed'), OR
    # 2. We have received normal readings at least merge_gap minutes after ended_at.
    for rec in persisted_records:
        if not rec.is_settled:
            should_settle = False
            if is_completing or shipment.status == "completed":
                should_settle = True
            elif last_reading_time and rec.ended_at:
                gap_since_end = (
                    last_reading_time - rec.ended_at
                ).total_seconds() / 60.0
                if gap_since_end >= merge_gap:
                    should_settle = True

            if should_settle:
                rec.is_settled = True
                db.flush()

                # Get all active lots currently on the shipment
                active_shipment_lots = list(
                    db.scalars(
                        select(ShipmentLot).where(
                            ShipmentLot.shipment_id == shipment.id,
                            ShipmentLot.unloaded_at.is_(None),
                        )
                    ).all()
                )

                for slot in active_shipment_lots:
                    event_service.append_event(
                        db,
                        principal,
                        slot.lot_id,
                        event_type="cold_chain_violation",
                        payload={
                            "shipment_id": str(shipment.id),
                            "shipment_code": shipment.shipment_code,
                            "container_code": shipment.container_code,
                            "reefer_container_code": shipment.container_code,
                            "violation_type": rec.violation_type,
                            "started_at": rec.started_at.isoformat(),
                            "ended_at": rec.ended_at.isoformat()
                            if rec.ended_at
                            else None,
                            "duration_minutes": float(rec.duration_minutes or 0),
                            "peak_temperature_celsius": float(
                                rec.peak_temperature_celsius
                            ),
                        },
                    )

    db.flush()
    return persisted_records


def ingest_telemetry_readings(
    db: Session,
    principal: Principal,
    payload: TelemetryIngestRequest,
) -> TelemetryIngestResponse:
    """Ingest a batch of container temperature readings (S-41, N3-59, N3-61, N3-62, N3-63)."""
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
            detail=f"Kh?ng t?m th?y chuy?n xe ?ang v?n chuy?n (in_transit) g?n v?i th?ng l?nh '{container_code}'.",
        )

    # 2. Authorization: carrier organization or system_admin
    if (
        principal.role != "system_admin"
        and shipment.organization_id != principal.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ch? ??n v? v?n chuy?n c?a chuy?n xe m?i ???c n?p d? li?u c?m bi?n.",
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
        existing_timestamps.add(rec_at)

    if values_to_insert:
        stmt = insert(TemperatureReading).values(values_to_insert)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["shipment_id", "recorded_at"]
        )
        db.execute(stmt)
        db.flush()

    # 5. Freeze (or reuse) the shipment's strictest per-product limits (N3-62)
    limits, _from_snapshot = cold_chain_config_service.get_or_snapshot_shipment_limits(
        db, shipment
    )

    # Update shipment last_reading_at = MAX(recorded_at)
    max_reading_at = db.scalar(
        select(func.max(TemperatureReading.recorded_at)).where(
            TemperatureReading.shipment_id == shipment.id
        )
    )
    if max_reading_at:
        shipment.last_reading_at = max_reading_at
        db.flush()

    # 6. Synchronize violations and log events
    persisted_violations = sync_shipment_violations_and_events(
        db, principal, shipment, is_completing=False
    )
    db.commit()

    all_readings_count = (
        db.scalar(
            select(func.count(TemperatureReading.id)).where(
                TemperatureReading.shipment_id == shipment.id
            )
        )
        or 0
    )

    violations_summary = [
        TelemetryViolationRead(
            id=v.id,
            shipment_id=v.shipment_id,
            violation_type=v.violation_type,
            started_at=v.started_at,
            ended_at=v.ended_at or v.started_at,
            duration_minutes=float(v.duration_minutes or 0),
            peak_temperature_celsius=float(v.peak_temperature_celsius),
            is_settled=v.is_settled,
        )
        for v in persisted_violations
    ]

    return TelemetryIngestResponse(
        container_code=container_code,
        shipment_id=shipment.id,
        shipment_code=shipment.shipment_code,
        ingested_count=len(values_to_insert),
        duplicate_count=duplicate_count,
        total_readings=all_readings_count,
        violations_detected=len(violations_summary),
        violations=violations_summary,
        applied_limits=limits.to_applied_read(from_snapshot=True),
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
            detail="Kh?ng t?m th?y chuy?n v?n chuy?n.",
        )

    if not _can_access_shipment(db, principal, shipment):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="B?n kh?ng c? quy?n xem d? li?u ?o c?a chuy?n xe n?y.",
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
    """Retrieve confirmed temperature violations for a given shipment."""
    shipment = db.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kh?ng t?m th?y chuy?n v?n chuy?n.",
        )

    if not _can_access_shipment(db, principal, shipment):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="B?n kh?ng c? quy?n xem d? li?u ?o c?a chuy?n xe n?y.",
        )

    records = list(
        db.scalars(
            select(ColdChainViolation)
            .where(ColdChainViolation.shipment_id == shipment_id)
            .order_by(ColdChainViolation.started_at.asc())
        ).all()
    )

    if not records:
        records = sync_shipment_violations_and_events(db, principal, shipment)
        db.commit()

    return [
        TelemetryViolationRead(
            id=r.id,
            shipment_id=r.shipment_id,
            violation_type=r.violation_type,
            started_at=r.started_at,
            ended_at=r.ended_at or r.started_at,
            duration_minutes=float(r.duration_minutes or 0),
            peak_temperature_celsius=float(r.peak_temperature_celsius),
            is_settled=r.is_settled,
        )
        for r in records
    ]
