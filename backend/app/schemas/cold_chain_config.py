"""Schemas for per-product cold chain threshold configuration (N3-62)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProductColdChainConfigUpsert(BaseModel):
    """Payload to create or replace the cold chain profile of one product."""

    min_temp_celsius: Decimal = Field(..., ge=Decimal("-50"), le=Decimal("80"))
    max_temp_celsius: Decimal = Field(..., ge=Decimal("-50"), le=Decimal("80"))
    delay_minutes: int = Field(..., ge=1, le=1440)

    @model_validator(mode="after")
    def validate_temperature_range(self) -> "ProductColdChainConfigUpsert":
        if self.min_temp_celsius >= self.max_temp_celsius:
            raise ValueError("Ngưỡng dưới phải nhỏ hơn ngưỡng trên.")
        return self


class ProductColdChainConfigRead(BaseModel):
    """Projection of the stored cold chain profile of one product."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    product_name: str
    min_temp_celsius: Decimal
    max_temp_celsius: Decimal
    delay_minutes: int
    updated_by_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class ProductColdChainLimitSourceRead(BaseModel):
    """Per-product contribution to a shipment's effective limits."""

    product_id: UUID | None = None
    product_name: str | None = None
    configured: bool = False
    min_temp_celsius: Decimal
    max_temp_celsius: Decimal
    delay_minutes: int


class AppliedColdChainLimitsRead(BaseModel):
    """The strictest limits actually applied when evaluating a shipment."""

    min_temp_celsius: Decimal
    max_temp_celsius: Decimal
    delay_minutes: int
    from_snapshot: bool


class ShipmentColdChainLimitsRead(BaseModel):
    """Effective cold chain limits of a shipment with per-product sources."""

    shipment_id: UUID
    shipment_code: str
    min_temp_celsius: Decimal
    max_temp_celsius: Decimal
    delay_minutes: int
    from_snapshot: bool
    config_resolved_at: datetime | None = None
    sources: list[ProductColdChainLimitSourceRead] = Field(default_factory=list)
