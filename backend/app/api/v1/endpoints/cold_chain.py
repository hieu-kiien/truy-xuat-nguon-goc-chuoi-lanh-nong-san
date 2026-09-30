from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import is_inspection_principal, require_permission
from app.core.database import get_db
from app.models.catalog import Product
from app.models.cold_chain import (
    ColdChainAlert,
    Sensor,
    Shipment,
    TemperatureReading,
)
from app.models.traceability import Lot, LotEvent
from app.schemas.traceability import (
    ColdChainAlertRead,
    Page,
    SensorCreate,
    SensorRead,
    TemperatureBatchCreate,
    TemperatureBatchResult,
)

router = APIRouter()


@router.post("/sensors", response_model=SensorRead, status_code=status.HTTP_201_CREATED)
@require_permission("sensors:write")
def create_sensor(
    payload: SensorCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Sensor:
    shipment = db.scalar(
        select(Shipment).where(
            Shipment.id == payload.shipment_id,
            Shipment.sender_organization_id == principal.organization_id,
            Shipment.status == "in_transit",
        )
    )
    if shipment is None:
        raise HTTPException(
            status_code=404, detail="Không tìm thấy chuyến đang do tổ chức vận chuyển."
        )
    sensor = Sensor(
        organization_id=principal.organization_id,
        shipment_id=shipment.id,
        device_code=payload.device_code.strip(),
        label=payload.label,
        is_active=True,
    )
    db.add(sensor)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(sensor)
    return sensor


@router.get("/sensors", response_model=Page[SensorRead])
@require_permission("sensors:read")
def list_sensors(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> Page[SensorRead]:
    base = select(Sensor)
    if not is_inspection_principal(principal):
        base = base.where(Sensor.organization_id == principal.organization_id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    sensors = db.scalars(
        base.order_by(Sensor.created_at.desc(), Sensor.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(items=list(sensors), page=page, page_size=page_size, total=total)


@router.post(
    "/sensors/{sensor_id}/readings",
    response_model=TemperatureBatchResult,
    status_code=status.HTTP_201_CREATED,
)
@require_permission("sensors:write")
def ingest_temperature_batch(
    sensor_id: UUID,
    payload: TemperatureBatchCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> TemperatureBatchResult:
    sensor = db.scalar(
        select(Sensor)
        .where(
            Sensor.id == sensor_id,
            Sensor.organization_id == principal.organization_id,
            Sensor.is_active.is_(True),
        )
        .with_for_update()
    )
    if sensor is None:
        raise HTTPException(
            status_code=404, detail="Không tìm thấy cảm biến đang hoạt động."
        )

    shipment = db.scalar(
        select(Shipment)
        .where(
            Shipment.id == sensor.shipment_id,
            Shipment.sender_organization_id == principal.organization_id,
            Shipment.status == "in_transit",
        )
        .with_for_update()
    )
    if shipment is None:
        raise HTTPException(
            status_code=409, detail="Chuyến vận chuyển không còn hoạt động."
        )

    now = datetime.now(UTC)
    for reading in payload.readings:
        if reading.measured_at < shipment.shipped_at:
            raise HTTPException(
                status_code=422, detail="Thời điểm đo không thể trước lúc xuất chuyến."
            )
        if reading.measured_at > now + timedelta(minutes=5):
            raise HTTPException(
                status_code=422, detail="Thời điểm đo không thể ở tương lai quá 5 phút."
            )

    lot = db.scalar(select(Lot).where(Lot.id == shipment.lot_id))
    if lot is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lô trong chuyến.")
    product = db.scalar(select(Product).where(Product.id == lot.product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm của lô.")

    rows = [
        {
            "id": uuid4(),
            "organization_id": principal.organization_id,
            "shipment_id": shipment.id,
            "sensor_id": sensor.id,
            "source_reading_id": reading.source_reading_id,
            "temperature_c": reading.temperature_c,
            "measured_at": reading.measured_at,
        }
        for reading in payload.readings
    ]
    insert_statement = (
        pg_insert(TemperatureReading.__table__)
        .values(rows)
        .on_conflict_do_nothing(constraint="uq_reading_source")
        .returning(
            TemperatureReading.id,
            TemperatureReading.temperature_c,
            TemperatureReading.measured_at,
        )
    )
    accepted = db.execute(insert_statement).all()
    if not accepted:
        db.commit()
        return TemperatureBatchResult(
            accepted=0, duplicates=len(payload.readings), alerts_created=0
        )

    temperatures = [row.temperature_c for row in accepted]
    shipment.temperature_min_c = min(
        [
            value
            for value in (shipment.temperature_min_c, min(temperatures))
            if value is not None
        ]
    )
    shipment.temperature_max_c = max(
        [
            value
            for value in (shipment.temperature_max_c, max(temperatures))
            if value is not None
        ]
    )

    alerts_created = 0
    for inserted in accepted:
        temperature = inserted.temperature_c
        below_min = (
            product.min_temperature_c is not None
            and temperature < product.min_temperature_c
        )
        above_max = (
            product.max_temperature_c is not None
            and temperature > product.max_temperature_c
        )
        if not (below_min or above_max):
            continue

        db.add(
            ColdChainAlert(
                organization_id=principal.organization_id,
                shipment_id=shipment.id,
                sensor_id=sensor.id,
                reading_id=inserted.id,
                temperature_c=temperature,
                min_temperature_c=product.min_temperature_c,
                max_temperature_c=product.max_temperature_c,
                status="open",
            )
        )
        db.add(
            LotEvent(
                lot_id=lot.id,
                # Anchor to the lot's owning organization, not the ingesting
                # party, so one lot's event history stays in a single tenant.
                organization_id=lot.organization_id,
                actor_user_id=principal.user_id,
                event_type="temperature_excursion",
                occurred_at=inserted.measured_at,
                public_note=None,
                details={
                    "temperature_c": str(temperature),
                    "min_temperature_c": (
                        str(product.min_temperature_c)
                        if product.min_temperature_c is not None
                        else None
                    ),
                    "max_temperature_c": (
                        str(product.max_temperature_c)
                        if product.max_temperature_c is not None
                        else None
                    ),
                },
            )
        )
        alerts_created += 1

    db.commit()
    return TemperatureBatchResult(
        accepted=len(accepted),
        duplicates=len(payload.readings) - len(accepted),
        alerts_created=alerts_created,
    )


@router.get("/alerts", response_model=Page[ColdChainAlertRead])
@require_permission("cold_chain:read")
def list_cold_chain_alerts(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    alert_status: str | None = Query(default=None, alias="status"),
) -> Page[ColdChainAlertRead]:
    base = select(ColdChainAlert).join(
        Shipment, Shipment.id == ColdChainAlert.shipment_id
    )
    if not is_inspection_principal(principal):
        base = base.where(
            or_(
                ColdChainAlert.organization_id == principal.organization_id,
                Shipment.sender_organization_id == principal.organization_id,
                Shipment.receiver_organization_id == principal.organization_id,
            )
        )
    if alert_status is not None:
        if alert_status not in {"open", "resolved"}:
            raise HTTPException(
                status_code=422, detail="Trạng thái cảnh báo không hợp lệ."
            )
        base = base.where(ColdChainAlert.status == alert_status)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    alerts = db.scalars(
        base.order_by(ColdChainAlert.created_at.desc(), ColdChainAlert.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(items=list(alerts), page=page, page_size=page_size, total=total)


@router.post("/alerts/{alert_id}/resolve", response_model=ColdChainAlertRead)
@require_permission("cold_chain:resolve")
def resolve_alert(
    alert_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> ColdChainAlert:
    alert = db.scalar(
        select(ColdChainAlert)
        .where(
            ColdChainAlert.id == alert_id,
            ColdChainAlert.organization_id == principal.organization_id,
        )
        .with_for_update()
    )
    if alert is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảnh báo.")
    if alert.status == "resolved":
        return alert
    alert.status = "resolved"
    alert.resolved_at = datetime.now(UTC)
    alert.resolved_by_id = principal.user_id
    db.commit()
    db.refresh(alert)
    return alert
