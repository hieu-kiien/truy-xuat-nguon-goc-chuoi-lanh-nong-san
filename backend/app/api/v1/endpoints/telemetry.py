"""API endpoints for cold chain telemetry ingestion and violation inspection (N3-60, S-41)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import require_permission
from app.core.database import get_db
from app.schemas.cold_chain_config import ShipmentColdChainLimitsRead
from app.schemas.telemetry import (
    TelemetryIngestRequest,
    TelemetryIngestResponse,
    TelemetryReadingRead,
    TelemetryViolationRead,
)
from app.services import cold_chain_config_service, telemetry_service

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
) -> list[TelemetryReadingRead]:
    return telemetry_service.list_shipment_readings(db, principal, shipment_id)


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
