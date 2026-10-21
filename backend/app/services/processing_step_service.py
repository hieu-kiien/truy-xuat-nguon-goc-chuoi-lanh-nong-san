"""Processing steps recorded for cooperative lots (N3-27).

A cooperative records that a lot went through a processing step together with
the parameters of that step. Every record becomes one event on the lot chain,
so the timeline shows the whole processing history. The public page only shows
the names of the steps, never the values.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.core.tenancy import get_tenant_record
from app.models.lot import Lot
from app.models.processing_step import LotProcessingStep, ProcessingStep
from app.schemas.processing import (
    ProcessingStepCreate,
    ProcessingStepRead,
    ProcessingStepRecordCreate,
    ProcessingStepRecordRead,
)
from app.services import event_service

logger = logging.getLogger(__name__)

PROCESSING_STEP_EVENT_TYPE = "processing_step_recorded"


def list_catalogue(db: Session, principal: Principal) -> list[ProcessingStepRead]:
    """Return the shared catalogue of processing steps."""
    rows = list(
        db.scalars(
            select(ProcessingStep)
            .where(ProcessingStep.is_active.is_(True))
            .order_by(ProcessingStep.name.asc())
        ).all()
    )
    return [
        ProcessingStepRead(
            id=row.id,
            code=row.code,
            name=row.name,
            parameter_schema=row.parameter_schema or {},
        )
        for row in rows
    ]


def create_catalogue_entry(
    db: Session, principal: Principal, payload: ProcessingStepCreate
) -> ProcessingStepRead:
    """Add one entry to the shared catalogue of processing steps."""
    code = payload.code.strip()
    existing = db.scalar(select(ProcessingStep.id).where(ProcessingStep.code == code))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Công đoạn '{code}' đã có trong danh mục.",
        )
    schema = payload.parameter_schema or {}
    malformed = sorted(
        name
        for name, rule in schema.items()
        if not isinstance(rule, dict) or not isinstance(rule.get("type"), str)
    )
    if malformed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Khai báo tham số của công đoạn phải là "
                '{"type": "number"} hoặc {"type": "string"}: ' + ", ".join(malformed)
            ),
        )
    step = ProcessingStep(
        code=code,
        name=payload.name.strip(),
        parameter_schema=schema,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return ProcessingStepRead(
        id=step.id,
        code=step.code,
        name=step.name,
        parameter_schema=step.parameter_schema or {},
    )


def _check_parameters(step: ProcessingStep, parameters: dict[str, Any]) -> None:
    """Refuse values that the schema of the step does not describe."""
    schema = step.parameter_schema or {}
    if not schema:
        return
    allowed = set(schema.keys())
    unexpected = sorted(set(parameters.keys()) - allowed)
    if unexpected:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Tham số không thuộc công đoạn '{step.code}': " + ", ".join(unexpected)
            ),
        )
    for name, rule in schema.items():
        if name not in parameters:
            continue
        if not isinstance(rule, dict):
            continue
        expected = rule.get("type")
        value = parameters[name]
        if expected == "number" and not isinstance(value, (int, float)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Tham số '{name}' phải là số.",
            )
        if expected == "string" and not isinstance(value, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Tham số '{name}' phải là chuỗi.",
            )


def record_processing_step(
    db: Session,
    principal: Principal,
    lot_id: UUID,
    payload: ProcessingStepRecordCreate,
) -> ProcessingStepRecordRead:
    """Record one processing step for a lot."""
    lot = get_tenant_record(db, Lot, lot_id, principal)
    if lot.current_holder_organization_id != principal.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ tổ chức đang giữ lô mới được ghi công đoạn chế biến.",
        )

    step = db.get(ProcessingStep, payload.processing_step_id)
    if step is None or not step.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Công đoạn chế biến không có trong danh mục.",
        )

    parameters = payload.parameters or {}
    _check_parameters(step, parameters)

    occurred_at = payload.occurred_at or datetime.now(UTC)
    record = LotProcessingStep(
        lot_id=lot.id,
        processing_step_id=step.id,
        parameters=parameters,
        occurred_at=occurred_at,
        organization_id=principal.organization_id,
        created_by_user_id=principal.user_id,
        created_at=datetime.now(UTC),
    )
    db.add(record)
    db.flush()

    # Mỗi công đoạn ghi thành một sự kiện trong chuỗi của lô (N3-27).
    event_service.append_event(
        db,
        principal,
        lot.id,
        event_type=PROCESSING_STEP_EVENT_TYPE,
        payload={
            "processing_step_id": str(step.id),
            "processing_step_code": step.code,
            "processing_step_name": step.name,
            "parameters": parameters,
            "occurred_at": occurred_at.isoformat(),
            "recorded_by_organization_id": str(principal.organization_id),
        },
    )
    db.commit()

    return ProcessingStepRecordRead(
        id=record.id,
        lot_id=record.lot_id,
        processing_step_id=step.id,
        processing_step_code=step.code,
        processing_step_name=step.name,
        parameters=record.parameters or {},
        occurred_at=record.occurred_at,
        organization_id=record.organization_id,
        created_at=record.created_at,
    )


def list_processing_steps(
    db: Session, principal: Principal, lot_id: UUID
) -> list[ProcessingStepRecordRead]:
    """List the processing steps recorded for a lot."""
    get_tenant_record(db, Lot, lot_id, principal, allow_historical=True)
    rows = list(
        db.execute(
            select(LotProcessingStep, ProcessingStep)
            .join(
                ProcessingStep,
                ProcessingStep.id == LotProcessingStep.processing_step_id,
            )
            .where(LotProcessingStep.lot_id == lot_id)
            .order_by(LotProcessingStep.occurred_at.asc())
        ).all()
    )
    return [
        ProcessingStepRecordRead(
            id=record.id,
            lot_id=record.lot_id,
            processing_step_id=step.id,
            processing_step_code=step.code,
            processing_step_name=step.name,
            parameters=record.parameters or {},
            occurred_at=record.occurred_at,
            organization_id=record.organization_id,
            created_at=record.created_at,
        )
        for record, step in rows
    ]
