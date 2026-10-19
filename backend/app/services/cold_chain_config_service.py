"""Per-product cold chain thresholds and shipment limit resolution (N3-62).

Business rules (N3-62 acceptance criteria):
- Mỗi loại sản phẩm có ngưỡng dưới, ngưỡng trên và độ trễ do quản trị hệ thống cấu hình.
- Chuyến chở nhiều loại hàng áp "ngưỡng chặt nhất": ngưỡng dưới lớn nhất,
  ngưỡng trên nhỏ nhất và độ trễ ngắn nhất trong các loại hàng đang trên chuyến
  (sản phẩm chưa cấu hình được bảo vệ bằng ngưỡng mặc định).
- Chuyến vận chuyển lưu snapshot ngưỡng hiệu lực khi mở chuyến; mọi lần nạp số đo
  và tính vi phạm dùng đúng snapshot đó — đổi cấu hình về sau không tính lại
  vi phạm đã ghi.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.core.tenancy import shared_select
from app.models.cold_chain_config import ProductColdChainConfig
from app.models.lot import Lot
from app.models.product import Product
from app.models.shipment import Shipment, ShipmentLot
from app.schemas.cold_chain_config import (
    AppliedColdChainLimitsRead,
    ProductColdChainConfigRead,
    ProductColdChainConfigUpsert,
    ProductColdChainLimitSourceRead,
    ShipmentColdChainLimitsRead,
)

logger = logging.getLogger(__name__)

# Fallback limits for products (or trips) without a configured profile.
# Matches the historical detector defaults from S-41/N3-61.
DEFAULT_MIN_TEMP_CELSIUS = Decimal("2.00")
DEFAULT_MAX_TEMP_CELSIUS = Decimal("8.00")
DEFAULT_DELAY_MINUTES = 30


@dataclass(frozen=True)
class ColdChainLimitSource:
    """One product's contribution to a shipment's effective limits."""

    product_id: UUID | None
    product_name: str | None
    configured: bool
    min_temp_celsius: Decimal
    max_temp_celsius: Decimal
    delay_minutes: int

    def to_read(self) -> ProductColdChainLimitSourceRead:
        return ProductColdChainLimitSourceRead(
            product_id=self.product_id,
            product_name=self.product_name,
            configured=self.configured,
            min_temp_celsius=self.min_temp_celsius,
            max_temp_celsius=self.max_temp_celsius,
            delay_minutes=self.delay_minutes,
        )


@dataclass(frozen=True)
class ResolvedColdChainLimits:
    """Strictest limits resolved across every product carried by a shipment."""

    min_temp_celsius: Decimal
    max_temp_celsius: Decimal
    delay_minutes: int
    sources: tuple[ColdChainLimitSource, ...]

    def to_applied_read(self, *, from_snapshot: bool) -> AppliedColdChainLimitsRead:
        return AppliedColdChainLimitsRead(
            min_temp_celsius=self.min_temp_celsius,
            max_temp_celsius=self.max_temp_celsius,
            delay_minutes=self.delay_minutes,
            from_snapshot=from_snapshot,
        )


def get_product_config(db: Session, product_id: UUID) -> ProductColdChainConfig | None:
    """Fetch the cold chain configuration of one product, if any."""
    return db.scalar(
        shared_select(ProductColdChainConfig).where(
            ProductColdChainConfig.product_id == product_id
        )
    )


def _to_config_read(config: ProductColdChainConfig) -> ProductColdChainConfigRead:
    return ProductColdChainConfigRead(
        id=config.id,
        product_id=config.product_id,
        product_name=config.product.name,
        min_temp_celsius=config.min_temp_celsius,
        max_temp_celsius=config.max_temp_celsius,
        delay_minutes=config.delay_minutes,
        updated_by_user_id=config.updated_by_user_id,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


def get_product_config_read(
    db: Session, product_id: UUID
) -> ProductColdChainConfigRead:
    """Read the stored configuration of a product or report 404."""
    config = get_product_config(db, product_id)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sản phẩm chưa được cấu hình ngưỡng chuỗi lạnh.",
        )
    return _to_config_read(config)


def upsert_product_config(
    db: Session,
    principal: Principal,
    product_id: UUID,
    payload: ProductColdChainConfigUpsert,
) -> ProductColdChainConfigRead:
    """Create or replace the cold chain profile of one product (system admin)."""
    product = db.scalar(shared_select(Product).where(Product.id == product_id))
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy sản phẩm.",
        )

    now = datetime.now(UTC)
    config = get_product_config(db, product_id)
    if config is None:
        config = ProductColdChainConfig(
            product_id=product_id,
            min_temp_celsius=payload.min_temp_celsius,
            max_temp_celsius=payload.max_temp_celsius,
            delay_minutes=payload.delay_minutes,
            updated_by_user_id=principal.user_id,
            created_at=now,
            updated_at=now,
        )
        db.add(config)
    else:
        config.min_temp_celsius = payload.min_temp_celsius
        config.max_temp_celsius = payload.max_temp_celsius
        config.delay_minutes = payload.delay_minutes
        config.updated_by_user_id = principal.user_id
        config.updated_at = now

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Không thể lưu cấu hình ngưỡng chuỗi lạnh.",
        ) from exc

    db.refresh(config)
    return _to_config_read(config)


def _resolve_limits_for_product_ids(
    db: Session, product_ids: list[UUID | None]
) -> ResolvedColdChainLimits:
    """Combine per-product profiles into the strictest effective limits.

    Strictest = highest lower bound, lowest upper bound, shortest delay.
    Products without a profile contribute the platform defaults so they stay
    protected; a trip with mixed incompatible profiles (e.g. leafy greens and
    frozen meat) conservatively flags everything outside every safe range.
    """
    unique_ids = sorted({pid for pid in product_ids if pid is not None})

    configs: dict[UUID, ProductColdChainConfig] = {}
    names: dict[UUID, str] = {}
    if unique_ids:
        configs = {
            config.product_id: config
            for config in db.scalars(
                shared_select(ProductColdChainConfig).where(
                    ProductColdChainConfig.product_id.in_(unique_ids)
                )
            ).all()
        }
        names = {
            product.id: product.name
            for product in db.scalars(
                shared_select(Product).where(Product.id.in_(unique_ids))
            ).all()
        }

    sources: list[ColdChainLimitSource] = []
    for product_id in unique_ids:
        config = configs.get(product_id)
        sources.append(
            ColdChainLimitSource(
                product_id=product_id,
                product_name=names.get(product_id),
                configured=config is not None,
                min_temp_celsius=(
                    config.min_temp_celsius if config else DEFAULT_MIN_TEMP_CELSIUS
                ),
                max_temp_celsius=(
                    config.max_temp_celsius if config else DEFAULT_MAX_TEMP_CELSIUS
                ),
                delay_minutes=(
                    config.delay_minutes if config else DEFAULT_DELAY_MINUTES
                ),
            )
        )

    if not sources:
        sources.append(
            ColdChainLimitSource(
                product_id=None,
                product_name=None,
                configured=False,
                min_temp_celsius=DEFAULT_MIN_TEMP_CELSIUS,
                max_temp_celsius=DEFAULT_MAX_TEMP_CELSIUS,
                delay_minutes=DEFAULT_DELAY_MINUTES,
            )
        )

    return ResolvedColdChainLimits(
        min_temp_celsius=max(s.min_temp_celsius for s in sources),
        max_temp_celsius=min(s.max_temp_celsius for s in sources),
        delay_minutes=min(s.delay_minutes for s in sources),
        sources=tuple(sources),
    )


def resolve_limits_for_lots(db: Session, lots: list[Lot]) -> ResolvedColdChainLimits:
    """Resolve strictest limits for a list of lots (e.g. at shipment creation)."""
    return _resolve_limits_for_product_ids(db, [lot.product_id for lot in lots])


def _active_shipment_product_ids(db: Session, shipment_id: UUID) -> list[UUID | None]:
    return list(
        db.scalars(
            select(Lot.product_id)
            .join(ShipmentLot, ShipmentLot.lot_id == Lot.id)
            .where(
                ShipmentLot.shipment_id == shipment_id,
                ShipmentLot.unloaded_at.is_(None),
            )
        ).all()
    )


def _snapshot_is_set(shipment: Shipment) -> bool:
    return (
        shipment.cold_chain_min_temp_celsius is not None
        and shipment.cold_chain_max_temp_celsius is not None
        and shipment.cold_chain_delay_minutes is not None
    )


def _limits_from_snapshot(shipment: Shipment) -> ResolvedColdChainLimits:
    return ResolvedColdChainLimits(
        min_temp_celsius=shipment.cold_chain_min_temp_celsius,  # type: ignore[arg-type]
        max_temp_celsius=shipment.cold_chain_max_temp_celsius,  # type: ignore[arg-type]
        delay_minutes=shipment.cold_chain_delay_minutes,  # type: ignore[arg-type]
        sources=(),
    )


def apply_snapshot_limits(shipment: Shipment, limits: ResolvedColdChainLimits) -> None:
    """Freeze resolved limits onto the shipment row (no commit; caller decides)."""
    shipment.cold_chain_min_temp_celsius = limits.min_temp_celsius
    shipment.cold_chain_max_temp_celsius = limits.max_temp_celsius
    shipment.cold_chain_delay_minutes = limits.delay_minutes
    shipment.cold_chain_config_resolved_at = datetime.now(UTC)


def get_or_snapshot_shipment_limits(
    db: Session, shipment: Shipment
) -> tuple[ResolvedColdChainLimits, bool]:
    """Limits used for violation evaluation; snapshot on first ingest if unset.

    Trips opened after N3-62 already carry a snapshot. Legacy trips (created
    before the migration) are resolved once at their next ingest and then
    frozen, so later configuration changes never recompute past evaluations.
    """
    if _snapshot_is_set(shipment):
        return _limits_from_snapshot(shipment), True

    limits = _resolve_limits_for_product_ids(
        db, _active_shipment_product_ids(db, shipment.id)
    )
    apply_snapshot_limits(shipment, limits)
    db.commit()
    logger.info(
        "Snapshot cold chain limits for legacy shipment %s: min=%s max=%s delay=%s",
        shipment.shipment_code,
        limits.min_temp_celsius,
        limits.max_temp_celsius,
        limits.delay_minutes,
    )
    return limits, True


def effective_shipment_limits(
    db: Session, shipment: Shipment
) -> tuple[ResolvedColdChainLimits, bool]:
    """Effective limits plus per-product sources, without persisting anything."""
    sources = _resolve_limits_for_product_ids(
        db, _active_shipment_product_ids(db, shipment.id)
    ).sources
    if _snapshot_is_set(shipment):
        snapshot = _limits_from_snapshot(shipment)
        return (
            ResolvedColdChainLimits(
                min_temp_celsius=snapshot.min_temp_celsius,
                max_temp_celsius=snapshot.max_temp_celsius,
                delay_minutes=snapshot.delay_minutes,
                sources=sources,
            ),
            True,
        )
    return _resolve_limits_for_product_ids(
        db, _active_shipment_product_ids(db, shipment.id)
    ), False


def _can_access_shipment(db: Session, principal: Principal, shipment: Shipment) -> bool:
    """Mirror of the telemetry visibility rule for shipment-scoped data."""
    if principal.role in {"system_admin", "inspector"}:
        return True
    if shipment.organization_id == principal.organization_id:
        return True
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


def read_shipment_limits(
    db: Session, principal: Principal, shipment_id: UUID
) -> ShipmentColdChainLimitsRead:
    """Inspect effective limits and their per-product sources for a shipment."""
    shipment = db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy chuyến vận chuyển.",
        )
    if not _can_access_shipment(db, principal, shipment):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xem ngưỡng chuỗi lạnh của chuyến xe này.",
        )

    limits, from_snapshot = effective_shipment_limits(db, shipment)
    return ShipmentColdChainLimitsRead(
        shipment_id=shipment.id,
        shipment_code=shipment.shipment_code,
        min_temp_celsius=limits.min_temp_celsius,
        max_temp_celsius=limits.max_temp_celsius,
        delay_minutes=limits.delay_minutes,
        from_snapshot=from_snapshot,
        config_resolved_at=shipment.cold_chain_config_resolved_at,
        sources=[source.to_read() for source in limits.sources],
    )
