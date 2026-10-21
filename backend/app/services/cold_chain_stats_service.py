"""Cold chain violation statistics grouped by carrier organization (N3-73).

The carrier of a cold shipment is the organization that owns the shipment and
runs the refrigerated container. Statistics are always scoped to what the
caller may legitimately see: their own shipments plus shipments that still
hold one of their lots. Inspectors and system administrators see every
carrier.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import and_, case, exists, func, or_, select, true
from sqlalchemy.orm import Session, aliased

from app.core.auth import Principal
from app.models.identity import Organization
from app.models.shipment import Shipment, ShipmentLot
from app.models.telemetry import ColdChainViolation
from app.schemas.cold_chain_stats import (
    CarrierViolationStatsRead,
    ColdChainViolationStatsRead,
)

logger = logging.getLogger(__name__)


def _visible_shipment_condition(principal: Principal):
    """Mirror the shipments RLS read policy used for telemetry inspection."""
    if principal.role in {"system_admin", "inspector"}:
        return true()
    holds_caller_lot = exists(
        select(ShipmentLot.id).where(
            ShipmentLot.shipment_id == Shipment.id,
            ShipmentLot.lot.has(
                current_holder_organization_id=principal.organization_id
            ),
        )
    )
    return or_(
        Shipment.organization_id == principal.organization_id,
        holds_caller_lot,
    )


def _violation_rate(shipment_count: int, shipment_with_violation_count: int) -> float:
    """Percentage of shipments that recorded at least one violation."""
    if shipment_count <= 0:
        return 0.0
    return round(shipment_with_violation_count * 100.0 / shipment_count, 2)


def summarize_violations_by_carrier(
    db: Session,
    principal: Principal,
    *,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> ColdChainViolationStatsRead:
    """Aggregate cold chain violations per carrier for the requested window.

    The window is applied to the moment a shipment was opened
    (``shipments.created_at``) and to the moment a violation started. A
    shipment is counted once even when it carries many violations.
    """
    if period_end is None:
        period_end = datetime.now(UTC)
    if period_start is not None and period_start > period_end:
        period_start, period_end = period_end, period_start

    carrier = aliased(Organization)
    violation_conditions = [
        ColdChainViolation.shipment_id == Shipment.id,
        ColdChainViolation.started_at <= period_end,
    ]
    if period_start is not None:
        violation_conditions.append(ColdChainViolation.started_at >= period_start)

    violated_shipment = case((ColdChainViolation.id.isnot(None), Shipment.id))

    statement = (
        select(
            Shipment.organization_id.label("carrier_organization_id"),
            func.coalesce(carrier.name, "").label("carrier_organization_name"),
            func.coalesce(carrier.organization_type, "").label(
                "carrier_organization_type"
            ),
            func.count(func.distinct(Shipment.id)).label("shipment_count"),
            func.count(func.distinct(violated_shipment)).label(
                "shipment_with_violation_count"
            ),
            func.count(ColdChainViolation.id).label("violation_count"),
            func.coalesce(
                func.sum(
                    case(
                        (ColdChainViolation.violation_type == "high_temp", 1),
                        else_=0,
                    )
                ),
                0,
            ).label("high_temp_violation_count"),
            func.coalesce(
                func.sum(
                    case(
                        (ColdChainViolation.violation_type == "low_temp", 1),
                        else_=0,
                    )
                ),
                0,
            ).label("low_temp_violation_count"),
            func.coalesce(func.sum(ColdChainViolation.duration_minutes), 0).label(
                "total_violation_minutes"
            ),
        )
        .select_from(Shipment)
        .outerjoin(
            ColdChainViolation,
            and_(*violation_conditions),
        )
        .outerjoin(carrier, carrier.id == Shipment.organization_id)
        .where(_visible_shipment_condition(principal))
        .where(Shipment.created_at <= period_end)
        .group_by(
            Shipment.organization_id,
            carrier.name,
            carrier.organization_type,
        )
        .order_by(func.count(ColdChainViolation.id).desc())
    )
    if period_start is not None:
        statement = statement.where(Shipment.created_at >= period_start)

    rows = db.execute(statement).all()

    carriers: list[CarrierViolationStatsRead] = []
    total_shipment_count = 0
    total_shipment_with_violation_count = 0
    total_violation_count = 0
    total_violation_minutes = Decimal("0")

    for row in rows:
        shipment_count = int(row.shipment_count or 0)
        shipment_with_violation_count = int(row.shipment_with_violation_count or 0)
        violation_count = int(row.violation_count or 0)
        minutes = row.total_violation_minutes or Decimal("0")

        carriers.append(
            CarrierViolationStatsRead(
                carrier_organization_id=row.carrier_organization_id,
                carrier_organization_name=row.carrier_organization_name or "",
                carrier_organization_type=row.carrier_organization_type or "",
                shipment_count=shipment_count,
                shipment_with_violation_count=shipment_with_violation_count,
                violation_count=violation_count,
                high_temp_violation_count=int(row.high_temp_violation_count or 0),
                low_temp_violation_count=int(row.low_temp_violation_count or 0),
                total_violation_minutes=round(float(minutes), 2),
                violation_shipment_rate=_violation_rate(
                    shipment_count, shipment_with_violation_count
                ),
            )
        )
        total_shipment_count += shipment_count
        total_shipment_with_violation_count += shipment_with_violation_count
        total_violation_count += violation_count
        total_violation_minutes += minutes

    return ColdChainViolationStatsRead(
        period_start=period_start,
        period_end=period_end,
        carriers=carriers,
        total_shipment_count=total_shipment_count,
        total_shipment_with_violation_count=total_shipment_with_violation_count,
        total_violation_count=total_violation_count,
        total_violation_minutes=round(float(total_violation_minutes), 2),
        violation_shipment_rate=_violation_rate(
            total_shipment_count, total_shipment_with_violation_count
        ),
    )
