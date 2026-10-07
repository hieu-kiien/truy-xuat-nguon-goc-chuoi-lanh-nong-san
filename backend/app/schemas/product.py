from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ProductUnitValue = Literal["kg", "tấn", "thùng"]


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    unit: ProductUnitValue
    description: str | None = None
    price: float = Field(default=0, ge=0)
    quantity: int | None = Field(default=0, ge=0)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    unit: ProductUnitValue | None = None
    description: str | None = None
    price: float | None = Field(default=None, ge=0)
    quantity: int | None = Field(default=None, ge=0)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ProductRead(ProductBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
