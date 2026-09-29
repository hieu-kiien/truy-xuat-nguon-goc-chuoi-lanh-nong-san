from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class Page[T](BaseModel):
    items: list[T]
    page: int
    page_size: int
    total: int


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=100)
    min_temperature_c: Decimal | None = Field(default=None, ge=-100, le=150)
    max_temperature_c: Decimal | None = Field(default=None, ge=-100, le=150)

    @model_validator(mode="after")
    def validate_temperature_range(self):
        if (
            self.min_temperature_c is not None
            and self.max_temperature_c is not None
            and self.min_temperature_c > self.max_temperature_c
        ):
            raise ValueError("Ngưỡng nhiệt độ tối thiểu phải nhỏ hơn tối đa.")
        return self


class ProductUpdate(ProductCreate):
    pass


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    category: str
    min_temperature_c: Decimal | None
    max_temperature_c: Decimal | None
    created_at: datetime


class LotStatus(StrEnum):
    created = "created"
    harvested = "harvested"
    processed = "processed"
    packed = "packed"
    in_transit = "in_transit"
    received = "received"
    stored = "stored"
    sold = "sold"
    discarded = "discarded"


class LotCreate(BaseModel):
    lot_number: str | None = Field(default=None, max_length=80)
    product_id: UUID
    origin_farm_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    unit: str = Field(min_length=1, max_length=24)
    harvested_at: datetime | None = None
    public_note: str | None = Field(default=None, max_length=500)


class LotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    public_code: str
    lot_number: str | None
    organization_id: UUID
    origin_organization_id: UUID
    product_id: UUID
    origin_farm_id: UUID
    quantity: Decimal
    unit: str
    status: LotStatus
    harvested_at: datetime | None
    created_by_id: UUID
    created_at: datetime


class LotEventType(StrEnum):
    harvested = "harvested"
    processed = "processed"
    packed = "packed"
    stored = "stored"
    inspection = "inspection"
    sold = "sold"
    discarded = "discarded"


class LotEventCreate(BaseModel):
    event_type: LotEventType
    occurred_at: datetime
    public_note: str | None = Field(default=None, max_length=500)
    details: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class LotEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lot_id: UUID
    organization_id: UUID
    actor_user_id: UUID | None
    event_type: str
    occurred_at: datetime
    public_note: str | None
    details: dict
    created_at: datetime


class LineageAllocation(BaseModel):
    lot_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=3)


class LotDeriveCreate(BaseModel):
    lot_number: str | None = Field(default=None, max_length=80)
    product_id: UUID
    origin_farm_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    unit: str = Field(min_length=1, max_length=24)
    relation_type: str
    source_allocations: list[LineageAllocation] = Field(min_length=1, max_length=100)
    public_note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_relation(self):
        if self.relation_type not in {"split", "merge"}:
            raise ValueError("relation_type chỉ nhận split hoặc merge.")
        source_ids = [item.lot_id for item in self.source_allocations]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("Không được lặp lô nguồn trong source_allocations.")
        return self


class LotLineageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    source_lot_id: UUID
    target_lot_id: UUID
    relation_type: str
    source_quantity: Decimal
    unit: str
    created_at: datetime


class ShipmentCreate(BaseModel):
    lot_id: UUID
    receiver_organization_id: UUID
    shipped_at: datetime


class ShipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lot_id: UUID
    sender_organization_id: UUID
    receiver_organization_id: UUID
    status: str
    shipped_at: datetime
    received_at: datetime | None
    temperature_min_c: Decimal | None
    temperature_max_c: Decimal | None
    created_by_id: UUID
    received_by_id: UUID | None
    created_at: datetime


class SensorCreate(BaseModel):
    shipment_id: UUID
    device_code: str = Field(min_length=1, max_length=80)
    label: str | None = Field(default=None, max_length=120)


class SensorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    shipment_id: UUID
    device_code: str
    label: str | None
    is_active: bool
    created_at: datetime


class TemperatureReadingInput(BaseModel):
    source_reading_id: str = Field(min_length=1, max_length=120)
    temperature_c: Decimal = Field(ge=-100, le=150, max_digits=8, decimal_places=3)
    measured_at: datetime

    @model_validator(mode="after")
    def require_timezone(self):
        if self.measured_at.tzinfo is None or self.measured_at.utcoffset() is None:
            raise ValueError("measured_at phải có múi giờ.")
        return self


class TemperatureBatchCreate(BaseModel):
    readings: list[TemperatureReadingInput] = Field(min_length=1, max_length=500)


class TemperatureBatchResult(BaseModel):
    accepted: int
    duplicates: int
    alerts_created: int


class ColdChainAlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shipment_id: UUID
    sensor_id: UUID
    reading_id: UUID
    temperature_c: Decimal
    min_temperature_c: Decimal | None
    max_temperature_c: Decimal | None
    status: str
    created_at: datetime
    resolved_at: datetime | None
    resolved_by_id: UUID | None


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    organization_type: str
    admin_email: EmailStr
    admin_full_name: str = Field(min_length=1, max_length=200)
    admin_password: str = Field(min_length=12, max_length=1024)


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    role_code: str
    password: str = Field(min_length=12, max_length=1024)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    role_code: str
    email: EmailStr
    full_name: str
    is_active: bool


class PublicTraceEvent(BaseModel):
    event_type: str
    occurred_at: datetime
    public_note: str | None


class PublicTraceNode(BaseModel):
    depth: int
    lot_number: str | None
    quantity: Decimal
    unit: str
    status: str
    harvested_at: datetime | None
    created_at: datetime
    organization_name: str
    product_name: str
    product_category: str
    farm_name: str
    events: list[PublicTraceEvent]


class PublicTraceLink(BaseModel):
    source_lot_number: str | None
    target_lot_number: str | None
    relation_type: str
    source_quantity: Decimal
    unit: str


class PublicTraceRead(BaseModel):
    lot: PublicTraceNode
    ancestry: list[PublicTraceNode]
    lineage: list[PublicTraceLink]
