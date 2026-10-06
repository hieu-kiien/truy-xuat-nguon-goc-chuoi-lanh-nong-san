from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ProductUnit = Literal["kg", "tấn", "thùng"]


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    unit: ProductUnit

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Tên sản phẩm không được để trống.")
        return value.strip()


class ProductUpdate(ProductCreate):
    pass


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    unit: ProductUnit
